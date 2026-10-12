import json
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.common.schemas import Page
from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.jobs import JobRunner
from app.core.utils import new_token, serialize_doc, to_object_id, utcnow
from app.modules.planner import agents
from app.modules.planner.budget import compute_budget
from app.modules.planner.enrichment import add_maps_links, assign_dates
from app.modules.planner.orchestrator import TripPlanner
from app.modules.planner.schemas import DayPlan, ItineraryDraft, TripPlan
from app.modules.trips.schemas import (
    ShareResponse,
    TripChatResponse,
    TripCreate,
    TripInputs,
    TripMessage,
    TripOut,
    TripProgress,
    TripStatus,
    TripSummary,
    TripUpdate,
)
from app.providers.registry import Providers

BUSY = [TripStatus.queued.value, TripStatus.generating.value]
SUMMARY_PROJECTION = {"plan": 0}
CHAT_HISTORY_TURNS = 6


def to_trip_out(doc: dict[str, Any]) -> TripOut:
    data = serialize_doc(doc)
    data["is_shared"] = bool(doc.get("share_token"))
    return TripOut.model_validate(data)


def to_summary(doc: dict[str, Any]) -> TripSummary:
    return TripSummary.model_validate(serialize_doc(doc))


class TripService:
    def __init__(self, db: AsyncDatabase, providers: Providers, settings: Settings, jobs: JobRunner):
        self.db, self.p, self.settings, self.jobs = db, providers, settings, jobs
        self.trips = db["trips"]
        self.messages = db["trip_messages"]

    # ─── CRUD ─────────────────────────────────────────────
    async def create(self, user: dict, data: TripCreate) -> TripOut:
        now = utcnow()
        inputs = TripInputs.model_validate(data.model_dump(exclude={"generate"}))
        doc = {
            **inputs.model_dump(mode="json"),
            "user_id": user["_id"],
            "status": TripStatus.draft.value,
            "progress": {"status": TripStatus.draft.value, "step": "", "percent": 0, "message": "Not generated yet", "updated_at": now},
            "plan": None,
            "plan_version": 0,
            "error": None,
            "share_token": None,
            "cover_image": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.trips.insert_one(doc)
        doc["_id"] = result.inserted_id
        if data.generate:
            doc = await self._queue(doc["_id"])
        return to_trip_out(doc)

    async def get_doc(self, user: dict, trip_id: str, projection: dict | None = None) -> dict:
        doc = await self.trips.find_one({"_id": to_object_id(trip_id, "Trip"), "user_id": user["_id"]}, projection)
        if doc is None:
            raise NotFoundError("Trip not found")
        return doc

    async def get(self, user: dict, trip_id: str) -> TripOut:
        return to_trip_out(await self.get_doc(user, trip_id))

    async def list_trips(self, user: dict, status: TripStatus | None, page: int, limit: int) -> Page[TripSummary]:
        query: dict[str, Any] = {"user_id": user["_id"]}
        if status:
            query["status"] = status.value
        cursor = self.trips.find(query, SUMMARY_PROJECTION).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
        docs = await cursor.to_list(limit)
        total = await self.trips.count_documents(query)
        return Page[TripSummary](items=[to_summary(d) for d in docs], total=total, page=page, limit=limit, has_more=page * limit < total)

    async def update(self, user: dict, trip_id: str, data: TripUpdate) -> TripOut:
        doc = await self.get_doc(user, trip_id)
        if doc["status"] in BUSY:
            raise ConflictError("Trip is being generated; try again when it finishes", code="trip_busy")
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return to_trip_out(doc)
        current = TripInputs.model_validate(doc).model_dump()
        if {"start_date", "end_date"} & changes.keys() or "duration_days" in changes:
            # Re-derive the date range from whatever the client sent.
            if "start_date" in changes and "end_date" not in changes and "duration_days" not in changes:
                current["end_date"] = None
            if "duration_days" in changes and "end_date" not in changes:
                current["end_date"] = None
        merged = TripInputs.model_validate({**current, **changes})
        updated = await self.trips.find_one_and_update(
            {"_id": doc["_id"]},
            {"$set": {**merged.model_dump(mode="json"), "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        return to_trip_out(updated)

    async def delete(self, user: dict, trip_id: str) -> None:
        doc = await self.get_doc(user, trip_id, {"_id": 1})
        await self.trips.delete_one({"_id": doc["_id"]})
        await self.messages.delete_many({"trip_id": doc["_id"]})

    # ─── Generation ───────────────────────────────────────
    async def _queue(self, trip_id: ObjectId) -> dict:
        now = utcnow()
        doc = await self.trips.find_one_and_update(
            {"_id": trip_id, "status": {"$nin": BUSY}},
            {"$set": {
                "status": TripStatus.queued.value,
                "progress": {"status": TripStatus.queued.value, "step": "queued", "percent": 2, "message": "Queued for planning", "updated_at": now},
                "error": None,
                "updated_at": now,
            }},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise ConflictError("Trip is already being generated", code="trip_busy")
        planner = TripPlanner(self.db, self.p, self.settings)
        self.jobs.submit(planner.run(trip_id), name=f"plan-{trip_id}")
        return doc

    async def regenerate(self, user: dict, trip_id: str) -> TripOut:
        doc = await self.get_doc(user, trip_id, {"_id": 1})
        return to_trip_out(await self._queue(doc["_id"]))

    async def progress(self, user: dict, trip_id: str) -> TripProgress:
        doc = await self.get_doc(user, trip_id, {"progress": 1, "status": 1})
        return TripProgress.model_validate({**doc["progress"], "status": doc["status"]})

    # ─── Chat edits ───────────────────────────────────────
    async def chat(self, user: dict, trip_id: str, message: str) -> TripChatResponse:
        doc = await self.get_doc(user, trip_id)
        if doc["status"] != TripStatus.ready.value or not doc.get("plan"):
            raise AppError("The trip plan must be ready before you can chat about it", code="trip_not_ready", status_code=409)

        inputs = TripInputs.model_validate(doc)
        plan = TripPlan.model_validate(doc["plan"])
        history_docs = await self.messages.find({"trip_id": doc["_id"]}).sort("created_at", -1).limit(CHAT_HISTORY_TURNS).to_list(CHAT_HISTORY_TURNS)
        history = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in reversed(history_docs))
        await self._save_message(doc["_id"], "user", message, None)

        compact_days = [d.model_dump(include={"day", "title", "notes", "items"}, mode="json") for d in plan.days]
        for d in compact_days:
            d["items"] = [{k: v for k, v in i.items() if k not in ("maps_url", "image")} for i in d["items"]]
        edit = await agents.edit_agent(self.p.llm, inputs, json.dumps(compact_days, separators=(",", ":")), message, history)

        version = doc.get("plan_version", 0)
        updated_doc = doc
        if edit.changed and edit.days:
            new_days = agents.normalise_days(ItineraryDraft(days=edit.days), inputs.duration_days).days
            old_weather = {d.day: d.weather for d in plan.days}
            old_images = {i.title.lower(): i.image for d in plan.days for i in d.items if i.image}
            plan.days = [DayPlan.model_validate(d.model_dump()) for d in new_days]
            for d in plan.days:
                d.weather = old_weather.get(d.day)
                for item in d.items:
                    item.image = old_images.get(item.title.lower())
            add_maps_links(plan, inputs.destination)
            assign_dates(plan, inputs.start_date)
            plan.budget = compute_budget(plan, inputs)
            version += 1
            updated_doc = await self.trips.find_one_and_update(
                {"_id": doc["_id"]},
                {"$set": {"plan": plan.model_dump(mode="json"), "plan_version": version, "updated_at": utcnow()}},
                return_document=ReturnDocument.AFTER,
            )
        reply = await self._save_message(doc["_id"], "assistant", edit.reply, version)
        return TripChatResponse(reply=reply, plan_updated=bool(edit.changed and edit.days), trip=to_trip_out(updated_doc))

    async def _save_message(self, trip_id: ObjectId, role: str, content: str, plan_version: int | None) -> TripMessage:
        doc = {"trip_id": trip_id, "role": role, "content": content, "plan_version": plan_version, "created_at": utcnow()}
        result = await self.messages.insert_one(doc)
        doc["_id"] = result.inserted_id
        return TripMessage.model_validate(serialize_doc(doc))

    async def history(self, user: dict, trip_id: str) -> list[TripMessage]:
        doc = await self.get_doc(user, trip_id, {"_id": 1})
        msgs = await self.messages.find({"trip_id": doc["_id"]}).sort("created_at", 1).to_list(500)
        return [TripMessage.model_validate(serialize_doc(m)) for m in msgs]

    # ─── Sharing ──────────────────────────────────────────
    async def share(self, user: dict, trip_id: str) -> ShareResponse:
        doc = await self.get_doc(user, trip_id, {"share_token": 1})
        token = doc.get("share_token") or new_token(16)
        await self.trips.update_one({"_id": doc["_id"]}, {"$set": {"share_token": token}})
        return ShareResponse(share_token=token, share_url=f"{self.settings.public_web_url.rstrip('/')}/shared/{token}")

    async def unshare(self, user: dict, trip_id: str) -> None:
        doc = await self.get_doc(user, trip_id, {"_id": 1})
        await self.trips.update_one({"_id": doc["_id"]}, {"$set": {"share_token": None}})

    async def get_shared(self, token: str) -> TripOut:
        doc = await self.trips.find_one({"share_token": token, "status": TripStatus.ready.value})
        if doc is None:
            raise NotFoundError("Shared trip not found")
        out = to_trip_out(doc)
        return out.model_copy(update={"additional_info": ""})  # don't leak private notes

