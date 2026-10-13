"""
Booking state machine:

    create ──► awaiting_confirmation ──confirm──► processing ──► confirmed
                     │   ▲                          │              │
                     │   └── payment declined ──────┘              └─cancel─► cancelled
                     ├── past confirm_before ──► expired
                     └── cancel ──► cancelled          supplier error ──► failed (+refund)

Nothing is ever booked without an explicit /confirm carrying the exact price the
user accepted. Chat and voice flows can only create `awaiting_confirmation`.
"""

from typing import Any

from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.common.schemas import Money, Page
from app.common.travel import ContactInfo, FlightOffer, TravelerInfo, parse_offer
from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError, GoneError, NotFoundError
from app.core.utils import serialize_doc, to_object_id, utcnow
from app.modules.bookings.schemas import BookingConfirm, BookingCreate, BookingOut, BookingStatus, BookingSummary
from app.modules.search.service import OfferStore
from app.modules.users.service import UserService
from app.providers.payments import PaymentIntent, PaymentStatus
from app.providers.registry import Providers

PRICE_TOLERANCE = 0.01


def to_booking_out(doc: dict[str, Any]) -> BookingOut:
    data = serialize_doc(doc)
    data["offer"] = parse_offer(doc["offer"])
    return BookingOut.model_validate(data)


def _same_price(a: Money, b: Money) -> bool:
    return a.currency.upper() == b.currency.upper() and abs(a.amount - b.amount) <= PRICE_TOLERANCE


class BookingService:
    def __init__(self, db: AsyncDatabase, providers: Providers, settings: Settings):
        self.db, self.p, self.settings = db, providers, settings
        self.col = db["bookings"]
        self.offers = OfferStore(db, settings.offer_ttl_minutes)

    async def _get(self, user: dict, booking_id: str) -> dict:
        doc = await self.col.find_one({"_id": to_object_id(booking_id, "Booking"), "user_id": user["_id"]})
        if doc is None:
            raise NotFoundError("Booking not found")
        return doc

    async def _set(self, doc: dict, values: dict, expect_status: BookingStatus | None = None) -> dict:
        query: dict = {"_id": doc["_id"]}
        if expect_status:
            query["status"] = expect_status.value
        return await self.col.find_one_and_update(query, {"$set": {**values, "updated_at": utcnow()}}, return_document=ReturnDocument.AFTER)

    # ─── Create (quote) ───────────────────────────────────
    async def create(self, user: dict, data: BookingCreate, idempotency_key: str | None) -> BookingOut:
        if idempotency_key:
            existing = await self.col.find_one({"user_id": user["_id"], "idempotency_key": idempotency_key})
            if existing:
                return to_booking_out(existing)

        offer = await self.offers.get(data.offer_id)
        if data.traveler_ids:
            saved = await UserService(self.db).get_travelers_by_ids(user, data.traveler_ids)
            travelers = [TravelerInfo.model_validate(t) for t in saved]
        else:
            travelers = data.travelers
        if isinstance(offer, FlightOffer) and len(travelers) != offer.passengers:
            raise AppError(f"This fare is for {offer.passengers} passenger(s) but {len(travelers)} traveler(s) were given", code="traveler_mismatch", status_code=422)

        trip_oid = None
        if data.trip_id:
            trip = await self.db["trips"].find_one({"_id": to_object_id(data.trip_id, "Trip"), "user_id": user["_id"]}, {"_id": 1})
            if trip is None:
                raise NotFoundError("Trip not found")
            trip_oid = trip["_id"]

        provider = self.p.inventory_for(offer.provider, offer.kind.value)
        quoted = await provider.quote(offer)
        intent = await self.p.payments.create_intent(quoted.price, {"user_id": str(user["_id"]), "offer_id": offer.offer_id})
        now = utcnow()
        doc = {
            "user_id": user["_id"],
            "idempotency_key": idempotency_key,
            "status": BookingStatus.awaiting_confirmation.value,
            "kind": quoted.kind.value,
            "provider": quoted.provider,
            "offer": quoted.model_dump(mode="json"),
            "price": quoted.price.model_dump(),
            "original_price": offer.price.model_dump(),
            "price_changed": not _same_price(quoted.price, offer.price),
            "travelers": [t.model_dump(mode="json") for t in travelers],
            "contact": data.contact.model_dump(mode="json"),
            "trip_id": trip_oid,
            "notes": data.notes,
            "payment": {"intent_id": intent.id, "provider": intent.provider, "status": intent.status.value, "amount": intent.amount.model_dump(), "client_secret": intent.client_secret},
            "confirm_before": quoted.expires_at or offer.expires_at,
            "provider_reference": None,
            "provider_data": {},
            "tickets": [],
            "failure_reason": None,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.col.insert_one(doc)
        except DuplicateKeyError:  # concurrent retry with the same Idempotency-Key
            return to_booking_out(await self.col.find_one({"user_id": user["_id"], "idempotency_key": idempotency_key}))
        doc["_id"] = result.inserted_id
        return to_booking_out(doc)

    # ─── Confirm (pay + book) ─────────────────────────────
    async def confirm(self, user: dict, booking_id: str, data: BookingConfirm) -> BookingOut:
        doc = await self._get(user, booking_id)
        if doc["status"] in (BookingStatus.confirmed.value, BookingStatus.processing.value):
            return to_booking_out(doc)  # idempotent retry
        if doc["status"] != BookingStatus.awaiting_confirmation.value:
            raise ConflictError(f"Booking is {doc['status']} and cannot be confirmed", code="invalid_booking_state")
        if doc.get("confirm_before") and doc["confirm_before"] < utcnow():
            await self._set(doc, {"status": BookingStatus.expired.value, "failure_reason": "Offer expired before confirmation"})
            raise GoneError("The price hold expired. Please search again.", code="offer_expired")
        price = Money.model_validate(doc["price"])
        if not _same_price(price, data.expected_total):
            raise ConflictError("The price changed. Review the new total and confirm again.", code="price_mismatch", details={"current_price": price.model_dump()})

        locked = await self._set(doc, {"status": BookingStatus.processing.value}, expect_status=BookingStatus.awaiting_confirmation)
        if locked is None:  # lost a race with a concurrent confirm
            return to_booking_out(await self._get(user, booking_id))

        intent = PaymentIntent.model_validate({**doc["payment"], "id": doc["payment"]["intent_id"], "amount": doc["payment"]["amount"]})
        intent = await self.p.payments.capture(intent, data.payment_token)
        if intent.status != PaymentStatus.succeeded:
            await self._set(locked, {"status": BookingStatus.awaiting_confirmation.value, "payment.status": intent.status.value, "failure_reason": intent.failure_reason})
            raise AppError(intent.failure_reason or "Payment failed", code="payment_failed", status_code=402)

        offer = parse_offer(doc["offer"])
        travelers = [TravelerInfo.model_validate(t) for t in doc["travelers"]]
        contact = ContactInfo.model_validate(doc["contact"])
        provider = self.p.inventory_for(offer.provider, offer.kind.value)
        try:
            result = await provider.book(offer, travelers, contact)
        except Exception as exc:
            refund = await self.p.payments.refund(intent)
            reason = getattr(exc, "message", None) or "Supplier could not complete the booking"
            updated = await self._set(locked, {"status": BookingStatus.failed.value, "payment.status": refund.status.value, "failure_reason": f"{reason}. Your payment has been refunded."})
            return to_booking_out(updated)

        status = BookingStatus.confirmed if result.status == "confirmed" else BookingStatus.processing
        values = {
            "status": status.value,
            "payment.status": intent.status.value,
            "provider_reference": result.provider_reference,
            "provider_data": result.raw,
            "tickets": result.tickets,
            "failure_reason": None,
        }
        if status == BookingStatus.confirmed:
            values["confirmed_at"] = utcnow()
        return to_booking_out(await self._set(locked, values))

    # ─── Cancel ───────────────────────────────────────────
    async def cancel(self, user: dict, booking_id: str) -> BookingOut:
        doc = await self._get(user, booking_id)
        status = doc["status"]
        if status == BookingStatus.awaiting_confirmation.value:
            return to_booking_out(await self._set(doc, {"status": BookingStatus.cancelled.value, "cancelled_at": utcnow()}))
        if status != BookingStatus.confirmed.value:
            raise ConflictError(f"A {status} booking cannot be cancelled", code="invalid_booking_state")
        offer = parse_offer(doc["offer"])
        provider = self.p.inventory_for(offer.provider, offer.kind.value)
        await provider.cancel(doc["provider_reference"], doc.get("provider_data") or {})
        intent = PaymentIntent.model_validate({**doc["payment"], "id": doc["payment"]["intent_id"]})
        refund = await self.p.payments.refund(intent)
        return to_booking_out(await self._set(doc, {"status": BookingStatus.cancelled.value, "payment.status": refund.status.value, "cancelled_at": utcnow()}))

    # ─── Read ─────────────────────────────────────────────
    async def get(self, user: dict, booking_id: str) -> BookingOut:
        return to_booking_out(await self._get(user, booking_id))

    async def list_bookings(self, user: dict, status: BookingStatus | None, trip_id: str | None, page: int, limit: int) -> Page[BookingSummary]:
        query: dict[str, Any] = {"user_id": user["_id"]}
        if status:
            query["status"] = status.value
        if trip_id:
            query["trip_id"] = to_object_id(trip_id, "Trip")
        docs = await self.col.find(query).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
        total = await self.col.count_documents(query)
        items = [
            BookingSummary(
                id=str(d["_id"]), status=d["status"], kind=d["kind"], title=d["offer"]["title"], price=Money.model_validate(d["price"]),
                provider_reference=d.get("provider_reference"), trip_id=str(d["trip_id"]) if d.get("trip_id") else None, created_at=d["created_at"],
            )
            for d in docs
        ]
        return Page[BookingSummary](items=items, total=total, page=page, limit=limit, has_more=page * limit < total)
