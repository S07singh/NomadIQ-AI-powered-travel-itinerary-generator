from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.common.schemas import APIModel, Money
from app.common.travel import AnyOffer, ContactInfo, OfferKind, TravelerInfo

MAX_TRAVELERS_PER_BOOKING = 9


class BookingStatus(StrEnum):
    awaiting_confirmation = "awaiting_confirmation"  # quoted; user must explicitly confirm + pay
    processing = "processing"                        # payment captured, supplier booking in flight/pending
    confirmed = "confirmed"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired"


class BookingCreate(APIModel):
    offer_id: str = Field(examples=["mock:fl_1a2b3c"])
    traveler_ids: list[str] = Field(default_factory=list, description="Saved traveler ids (preferred for one-tap/voice)")
    travelers: list[TravelerInfo] = Field(default_factory=list, description="Inline traveler details")
    contact: ContactInfo
    trip_id: str | None = Field(default=None, description="Attach the booking to a trip")
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _one_source(self) -> "BookingCreate":
        if bool(self.traveler_ids) == bool(self.travelers):
            raise ValueError("provide either traveler_ids or travelers (exactly one)")
        if len(self.traveler_ids) + len(self.travelers) > MAX_TRAVELERS_PER_BOOKING:
            raise ValueError(f"at most {MAX_TRAVELERS_PER_BOOKING} travelers per booking")
        return self


class BookingConfirm(APIModel):
    expected_total: Money = Field(description="Price the user saw and accepted; booking is refused if it differs")
    payment_token: str | None = Field(default=None, description="Token from the payment SDK (Razorpay/Stripe)")


class PaymentInfo(APIModel):
    intent_id: str
    provider: str
    status: str
    amount: Money
    client_secret: str | None = None


class BookingOut(APIModel):
    id: str
    status: BookingStatus
    kind: OfferKind
    provider: str
    offer: AnyOffer
    price: Money
    original_price: Money | None = None
    price_changed: bool = False
    travelers: list[TravelerInfo]
    contact: ContactInfo | None = None
    trip_id: str | None = None
    notes: str = ""
    provider_reference: str | None = None
    tickets: list[str] = []
    payment: PaymentInfo | None = None
    confirm_before: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None


class BookingSummary(APIModel):
    id: str
    status: BookingStatus
    kind: OfferKind
    title: str
    price: Money
    provider_reference: str | None = None
    trip_id: str | None = None
    created_at: datetime
