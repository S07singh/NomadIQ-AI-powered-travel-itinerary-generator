from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.core.exceptions import AppError, NotFoundError
from app.core.utils import serialize_doc, to_object_id, utcnow
from app.modules.users.schemas import (
    DeviceOut,
    DeviceRegister,
    TravelerCreate,
    TravelerOut,
    TravelerUpdate,
    UserOut,
    UserPreferences,
    UserUpdate,
)

MAX_TRAVELERS = 20


def to_user_out(user: dict[str, Any]) -> UserOut:
    return UserOut.model_validate(serialize_doc(user))


class UserService:
    def __init__(self, db: AsyncDatabase):
        self.db = db

    # ─── Profile ──────────────────────────────────────────
    async def update_profile(self, user: dict, data: UserUpdate) -> UserOut:
        values: dict[str, Any] = {}
        if data.name is not None:
            values["name"] = data.name
        if data.avatar_url is not None:
            values["avatar_url"] = data.avatar_url
        if data.preferences is not None:
            current = UserPreferences.model_validate(user.get("preferences") or {})
            merged = current.model_copy(update=data.preferences.model_dump(exclude_unset=True, exclude_none=True))
            values["preferences"] = UserPreferences.model_validate(merged.model_dump()).model_dump(mode="json")
        if not values:
            return to_user_out(user)
        values["updated_at"] = utcnow()
        updated = await self.db["users"].find_one_and_update({"_id": user["_id"]}, {"$set": values}, return_document=ReturnDocument.AFTER)
        return to_user_out(updated)

    async def delete_account(self, user: dict) -> None:
        """Hard-delete personal data (store/GDPR requirement). Bookings are kept but anonymised for accounting."""
        uid: ObjectId = user["_id"]
        trip_ids = [t["_id"] async for t in self.db["trips"].find({"user_id": uid}, {"_id": 1})]
        conv_ids = [c["_id"] async for c in self.db["conversations"].find({"user_id": uid}, {"_id": 1})]
        await self.db["trip_messages"].delete_many({"trip_id": {"$in": trip_ids}})
        await self.db["conversation_messages"].delete_many({"conversation_id": {"$in": conv_ids}})
        for name in ("trips", "conversations", "travelers", "devices", "refresh_tokens"):
            await self.db[name].delete_many({"user_id": uid})
        await self.db["bookings"].update_many({"user_id": uid}, {"$set": {"travelers": [], "contact": None, "user_deleted": True}})
        await self.db["users"].delete_one({"_id": uid})

    # ─── Saved travelers ──────────────────────────────────
    async def list_travelers(self, user: dict) -> list[TravelerOut]:
        docs = await self.db["travelers"].find({"user_id": user["_id"]}).sort("created_at", 1).to_list(MAX_TRAVELERS)
        return [TravelerOut.model_validate(serialize_doc(d)) for d in docs]

    async def create_traveler(self, user: dict, data: TravelerCreate) -> TravelerOut:
        if await self.db["travelers"].count_documents({"user_id": user["_id"]}) >= MAX_TRAVELERS:
            raise AppError(f"You can save up to {MAX_TRAVELERS} travelers", code="limit_reached", status_code=409)
        now = utcnow()
        doc = {**data.model_dump(mode="json"), "user_id": user["_id"], "created_at": now, "updated_at": now}
        result = await self.db["travelers"].insert_one(doc)
        doc["_id"] = result.inserted_id
        return TravelerOut.model_validate(serialize_doc(doc))

    async def update_traveler(self, user: dict, traveler_id: str, data: TravelerUpdate) -> TravelerOut:
        values = data.model_dump(mode="json", exclude_unset=True)
        values["updated_at"] = utcnow()
        doc = await self.db["travelers"].find_one_and_update(
            {"_id": to_object_id(traveler_id, "Traveler"), "user_id": user["_id"]},
            {"$set": values},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise NotFoundError("Traveler not found")
        return TravelerOut.model_validate(serialize_doc(doc))

    async def delete_traveler(self, user: dict, traveler_id: str) -> None:
        result = await self.db["travelers"].delete_one({"_id": to_object_id(traveler_id, "Traveler"), "user_id": user["_id"]})
        if result.deleted_count == 0:
            raise NotFoundError("Traveler not found")

    async def get_travelers_by_ids(self, user: dict, ids: list[str]) -> list[dict]:
        oids = [to_object_id(i, "Traveler") for i in ids]
        docs = await self.db["travelers"].find({"_id": {"$in": oids}, "user_id": user["_id"]}).to_list(len(oids))
        by_id = {str(d["_id"]): d for d in docs}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise NotFoundError("Traveler not found", details={"missing": missing})
        return [by_id[i] for i in ids]

    # ─── Push devices ─────────────────────────────────────
    async def register_device(self, user: dict, data: DeviceRegister) -> DeviceOut:
        now = utcnow()
        doc = await self.db["devices"].find_one_and_update(
            {"token": data.token},
            {"$set": {**data.model_dump(), "user_id": user["_id"], "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return DeviceOut.model_validate(serialize_doc(doc))

    async def remove_device(self, user: dict, token: str) -> None:
        await self.db["devices"].delete_one({"token": token, "user_id": user["_id"]})
