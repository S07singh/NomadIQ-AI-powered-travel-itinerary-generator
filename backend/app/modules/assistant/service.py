"""
Conversational travel assistant (text + voice).

One LLM call classifies intent and extracts parameters, then the server runs the
action with the same services the REST API uses. Booking intents only ever
produce a quote (`awaiting_confirmation`) — the user must confirm in the UI.
"""

from datetime import date
from typing import Any

from bson import ObjectId
from pydantic import ValidationError
from pymongo.asynchronous.database import AsyncDatabase

from app.common.schemas import Page
from app.common.travel import (
    ActivitySearchRequest,
    FlightSearchRequest,
    GroundSearchRequest,
    HotelSearchRequest,
    OfferKind,
)
from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError
from app.core.jobs import JobRunner
from app.core.utils import serialize_doc, to_object_id, utcnow
from app.modules.assistant.schemas import (
    AssistantAction,
    AssistantDecision,
    AssistantIntent,
    AssistantMessage,
    AssistantMessageRequest,
    AssistantReply,
    ConversationSummary,
)
from app.modules.bookings.schemas import BookingCreate
from app.modules.bookings.service import BookingService
from app.modules.search.service import SearchService
from app.modules.trips.schemas import TripCreate
from app.modules.trips.service import TripService
from app.providers.registry import Providers

HISTORY_TURNS = 8
MAX_OFFERS_IN_CHAT = 5

SYSTEM = """You are NomadIQ, a friendly travel assistant inside a mobile/web app.
Classify the user's latest message into one intent and extract params with EXACT field names:
- plan_trip: destination, duration_days, start_date (YYYY-MM-DD), origin, budget {amount, currency}, travel_style (backpacker|budget|comfort|luxury), vibes, interests
- search_flights: origin (IATA), destination (IATA), departure_date, return_date, adults, cabin_class (economy|premium_economy|business|first)
- search_hotels: city, country_code (ISO-2), check_in, check_out, adults, rooms
- search_trains / search_buses: origin, destination, date, passengers, travel_class
- search_activities: destination, date, query
- book_offer: offer_id (use SELECTED_OFFER_ID when the user says "book this/that")
- modify_trip: request (the change, in the user's words) — only when TRIP_ID is set
- chat: anything else (questions, small talk); answer in `reply`
Resolve relative dates ("next Friday") using TODAY. Put required-but-unknown fields in `missing`.
Keep `reply` under 40 words; it may be spoken aloud."""


class AssistantService:
    def __init__(self, db: AsyncDatabase, providers: Providers, settings: Settings, jobs: JobRunner):
        self.db, self.p, self.settings, self.jobs = db, providers, settings, jobs
        self.conversations = db["conversations"]
        self.messages = db["conversation_messages"]

    # ─── Conversations ────────────────────────────────────
    async def _conversation(self, user: dict, conversation_id: str | None, first_message: str) -> dict:
        if conversation_id:
            conv = await self.conversations.find_one({"_id": to_object_id(conversation_id, "Conversation"), "user_id": user["_id"]})
            if conv is None:
                raise NotFoundError("Conversation not found")
            return conv
        now = utcnow()
        conv = {"user_id": user["_id"], "title": first_message[:60], "created_at": now, "updated_at": now}
        conv["_id"] = (await self.conversations.insert_one(conv)).inserted_id
        return conv

    async def _save(self, conv_id: ObjectId, role: str, content: str, intent: AssistantIntent | None = None, actions: list[AssistantAction] | None = None) -> AssistantMessage:
        doc = {
            "conversation_id": conv_id,
            "role": role,
            "content": content,
            "intent": intent.value if intent else None,
            "actions": [a.model_dump(mode="json") for a in actions or []],
            "created_at": utcnow(),
        }
        doc["_id"] = (await self.messages.insert_one(doc)).inserted_id
        await self.conversations.update_one({"_id": conv_id}, {"$set": {"updated_at": doc["created_at"]}})
        return AssistantMessage.model_validate(serialize_doc(doc))

    async def list_conversations(self, user: dict, page: int, limit: int) -> Page[ConversationSummary]:
        query = {"user_id": user["_id"]}
        docs = await self.conversations.find(query).sort("updated_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
        total = await self.conversations.count_documents(query)
        return Page[ConversationSummary](items=[ConversationSummary.model_validate(serialize_doc(d)) for d in docs], total=total, page=page, limit=limit, has_more=page * limit < total)

    async def get_messages(self, user: dict, conversation_id: str) -> list[AssistantMessage]:
        conv = await self._conversation(user, conversation_id, "")
        docs = await self.messages.find({"conversation_id": conv["_id"]}).sort("created_at", 1).to_list(1000)
        return [AssistantMessage.model_validate(serialize_doc(d)) for d in docs]

    async def delete_conversation(self, user: dict, conversation_id: str) -> None:
        conv = await self._conversation(user, conversation_id, "")
        await self.messages.delete_many({"conversation_id": conv["_id"]})
        await self.conversations.delete_one({"_id": conv["_id"]})

    # ─── Main entry ───────────────────────────────────────
    async def handle(self, user: dict, req: AssistantMessageRequest, transcript: str | None = None) -> AssistantReply:
        conv = await self._conversation(user, req.conversation_id, req.message)
        history = await self.messages.find({"conversation_id": conv["_id"]}).sort("created_at", -1).limit(HISTORY_TURNS).to_list(HISTORY_TURNS)
        await self._save(conv["_id"], "user", req.message)

        prefs = user.get("preferences") or {}
        prompt = "\n".join([
            f"TODAY: {date.today().isoformat()}",
            f"USER_HOME: city={prefs.get('home_city') or 'unknown'}, airport={prefs.get('home_airport') or 'unknown'}, currency={prefs.get('currency', 'USD')}",
            f"TRIP_ID: {req.trip_id or 'none'}",
            f"SELECTED_OFFER_ID: {req.selected_offer_id or ''}",
            "HISTORY:",
            *[f"  {m['role']}: {m['content'][:300]}" for m in reversed(history)],
            f"USER_MESSAGE: {req.message}",
        ])
        decision = await self.p.llm.generate_json(prompt, AssistantDecision, system=SYSTEM, temperature=0.2)
        reply, actions = await self._execute(user, req, decision)
        message = await self._save(conv["_id"], "assistant", reply, decision.intent, actions)
        return AssistantReply(conversation_id=str(conv["_id"]), message=message, transcript=transcript)

    async def _execute(self, user: dict, req: AssistantMessageRequest, d: AssistantDecision) -> tuple[str, list[AssistantAction]]:
        params = {k: v for k, v in (d.params or {}).items() if v not in (None, "", [])}
        prefs = user.get("preferences") or {}
        currency = prefs.get("currency", "USD")
        try:
            if d.intent == AssistantIntent.plan_trip:
                params.setdefault("travel_style", prefs.get("travel_style", "comfort"))
                if prefs.get("home_city"):
                    params.setdefault("origin", prefs["home_city"])
                trip = await TripService(self.db, self.p, self.settings, self.jobs).create(user, TripCreate.model_validate(params))
                return d.reply or f"Planning your trip to {trip.destination}…", [AssistantAction(type="trip_created", data={"trip_id": trip.id, "status": trip.status.value, "destination": trip.destination})]

            search = SearchService(self.db, self.p, self.settings)
            if d.intent == AssistantIntent.search_flights:
                if prefs.get("home_airport"):
                    params.setdefault("origin", prefs["home_airport"])
                params.setdefault("currency", currency)
                res = await search.flights(FlightSearchRequest.model_validate(params))
                return self._offers_reply(d, res.results, "flight")
            if d.intent == AssistantIntent.search_hotels:
                params.setdefault("currency", currency)
                res = await search.hotels(HotelSearchRequest.model_validate(params))
                return self._offers_reply(d, res.results, "hotel")
            if d.intent in (AssistantIntent.search_trains, AssistantIntent.search_buses):
                mode = OfferKind.train if d.intent == AssistantIntent.search_trains else OfferKind.bus
                res = await search.ground(mode, GroundSearchRequest.model_validate(params))
                return self._offers_reply(d, res.results, mode.value)
            if d.intent == AssistantIntent.search_activities:
                params.setdefault("currency", currency)
                res = await search.activities(ActivitySearchRequest.model_validate(params))
                return self._offers_reply(d, res.results, "activity")

            if d.intent == AssistantIntent.book_offer:
                return await self._quote_booking(user, params.get("offer_id") or req.selected_offer_id)

            if d.intent == AssistantIntent.modify_trip:
                if not req.trip_id:
                    return "Open the trip you want to change and ask me again.", [AssistantAction(type="needs_info", data={"missing": ["trip_id"]})]
                result = await TripService(self.db, self.p, self.settings, self.jobs).chat(user, req.trip_id, params.get("request") or req.message)
                return result.reply.content, [AssistantAction(type="trip_updated", data={"trip_id": req.trip_id, "plan_updated": result.plan_updated, "plan_version": result.trip.plan_version})]
        except ValidationError as exc:
            missing = sorted({str(e["loc"][0]) for e in exc.errors() if e.get("loc")} | set(d.missing))
            return self._ask_for(missing), [AssistantAction(type="needs_info", data={"intent": d.intent.value, "missing": missing, "params": params})]
        except AppError as exc:
            return exc.message, []

        if d.missing:
            return d.reply or self._ask_for(d.missing), [AssistantAction(type="needs_info", data={"intent": d.intent.value, "missing": d.missing})]
        return d.reply or "How can I help with your trip?", []

    @staticmethod
    def _ask_for(missing: list[str]) -> str:
        nice = ", ".join(m.replace("_", " ") for m in missing) or "a few more details"
        return f"Could you tell me the {nice}?"

    @staticmethod
    def _offers_reply(d: AssistantDecision, offers: list, kind: str) -> tuple[str, list[AssistantAction]]:
        if not offers:
            return f"I couldn't find any {kind} options for that. Want to try different dates?", []
        by_price = sorted(offers, key=lambda o: o.price.amount)
        top, cheapest = by_price[:MAX_OFFERS_IN_CHAT], by_price[0]
        text = d.reply or f"I found {len(offers)} {kind} options."
        text += f" Cheapest: {cheapest.title} at {cheapest.price.amount:,.0f} {cheapest.price.currency}."
        return text, [AssistantAction(type="show_offers", data={"kind": kind, "total": len(offers), "results": [o.model_dump(mode="json") for o in top]})]

    async def _quote_booking(self, user: dict, offer_id: str | None) -> tuple[str, list[AssistantAction]]:
        if not offer_id:
            return "Which option should I book? Select one and say “book this”.", [AssistantAction(type="needs_info", data={"missing": ["offer_id"]})]
        travelers = await self.db["travelers"].find({"user_id": user["_id"]}).sort("created_at", 1).to_list(1)
        if not travelers:
            return "Add your traveler details in Profile → Travelers first, then I can book in one step.", [AssistantAction(type="needs_info", data={"missing": ["saved_traveler"]})]
        lead = travelers[0]
        contact: dict[str, Any] = {"email": lead.get("email") or user["email"], "phone": lead.get("phone") or ""}
        if len(contact["phone"]) < 6:
            return "I need a phone number on your traveler profile to book.", [AssistantAction(type="needs_info", data={"missing": ["phone"]})]
        booking = await BookingService(self.db, self.p, self.settings).create(
            user, BookingCreate(offer_id=offer_id, traveler_ids=[str(lead["_id"])], contact=contact), idempotency_key=None
        )
        price = booking.price
        text = f"I've held {booking.offer.title} at {price.amount:,.0f} {price.currency}. Review and tap Confirm to pay and book."
        return text, [AssistantAction(type="booking_quote", data={"booking_id": booking.id, "requires_confirmation": True, "price": price.model_dump(), "confirm_before": booking.confirm_before.isoformat() if booking.confirm_before else None})]
