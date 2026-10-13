"""
Provider-agnostic travel inventory schemas (search requests + bookable offers).

Every offer carries `offer_id` of the form "<provider>:<provider_offer_id>" so a
booking can be routed back to the provider that produced it.
"""

from datetime import date, datetime
from datetime import date as Date
from enum import StrEnum
from typing import Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.common.schemas import APIModel, MediaImage, Money


class OfferKind(StrEnum):
    flight = "flight"
    hotel = "hotel"
    train = "train"
    bus = "bus"
    activity = "activity"


class CabinClass(StrEnum):
    economy = "economy"
    premium_economy = "premium_economy"
    business = "business"
    first = "first"


class PassengerType(StrEnum):
    adult = "adult"
    child = "child"
    infant = "infant"


def _not_in_past(cls, value: date) -> date:
    if value < date.today():
        raise ValueError("date must not be in the past")
    return value


# ─── Search requests ──────────────────────────────────────────────

class FlightSearchRequest(APIModel):
    origin: str = Field(min_length=3, max_length=3, description="IATA airport/city code", examples=["DEL"])
    destination: str = Field(min_length=3, max_length=3, examples=["BOM"])
    departure_date: date
    return_date: date | None = None
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=8)
    infants: int = Field(default=0, ge=0, le=4)
    cabin_class: CabinClass = CabinClass.economy
    currency: str = Field(default="USD", min_length=3, max_length=3)
    non_stop_only: bool = False
    max_results: int = Field(default=20, ge=1, le=50)

    _future = field_validator("departure_date")(_not_in_past)

    @field_validator("origin", "destination", "currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def _check(self) -> "FlightSearchRequest":
        if self.return_date and self.return_date < self.departure_date:
            raise ValueError("return_date must be on or after departure_date")
        if self.origin == self.destination:
            raise ValueError("origin and destination must differ")
        if self.infants > self.adults:
            raise ValueError("each infant needs an accompanying adult")
        return self


class HotelSearchRequest(APIModel):
    city: str = Field(min_length=2, max_length=100, examples=["Goa"])
    country_code: str | None = Field(default=None, min_length=2, max_length=2, examples=["IN"])
    check_in: date
    check_out: date
    adults: int = Field(default=2, ge=1, le=16)
    children: int = Field(default=0, ge=0, le=10)
    rooms: int = Field(default=1, ge=1, le=8)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    max_price_per_night: float | None = Field(default=None, gt=0)
    max_results: int = Field(default=20, ge=1, le=50)

    _future = field_validator("check_in")(_not_in_past)

    @model_validator(mode="after")
    def _check(self) -> "HotelSearchRequest":
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if (self.check_out - self.check_in).days > 30:
            raise ValueError("stays longer than 30 nights are not supported")
        return self

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


class GroundSearchRequest(APIModel):
    origin: str = Field(min_length=2, max_length=100, description="City or station code", examples=["New Delhi"])
    destination: str = Field(min_length=2, max_length=100, examples=["Jaipur"])
    date: Date
    passengers: int = Field(default=1, ge=1, le=6)
    travel_class: str | None = Field(default=None, examples=["3A", "SL", "sleeper", "seater"])
    currency: str = Field(default="INR", min_length=3, max_length=3)
    max_results: int = Field(default=20, ge=1, le=50)

    _future = field_validator("date")(_not_in_past)


class ActivitySearchRequest(APIModel):
    destination: str = Field(min_length=2, max_length=100)
    date: Date | None = None
    query: str | None = Field(default=None, max_length=100, examples=["food tour"])
    currency: str = Field(default="USD", min_length=3, max_length=3)
    max_results: int = Field(default=20, ge=1, le=50)


# ─── Offers ───────────────────────────────────────────────────────

class BaseOffer(APIModel):
    offer_id: str
    kind: OfferKind
    provider: str
    title: str
    price: Money
    refundable: bool = False
    expires_at: datetime | None = None
    deep_link: str | None = Field(default=None, description="Provider page if in-app booking is unavailable")


class FlightSegment(APIModel):
    carrier: str
    carrier_code: str
    flight_number: str
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    aircraft: str | None = None


class FlightSlice(APIModel):
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    stops: int
    segments: list[FlightSegment]


class FlightOffer(BaseOffer):
    kind: Literal[OfferKind.flight] = OfferKind.flight
    slices: list[FlightSlice]
    cabin_class: CabinClass = CabinClass.economy
    passengers: int = 1
    baggage: str | None = None
    airline_logo_url: str | None = None


class HotelOffer(BaseOffer):
    kind: Literal[OfferKind.hotel] = OfferKind.hotel
    hotel_id: str
    name: str
    address: str = ""
    city: str = ""
    star_rating: float | None = None
    review_score: float | None = None
    lat: float | None = None
    lng: float | None = None
    images: list[MediaImage] = []
    room_name: str = ""
    board_type: str = Field(default="room_only", examples=["room_only", "breakfast_included"])
    check_in: date
    check_out: date
    nights: int
    price_per_night: Money
    amenities: list[str] = []
    cancellation_policy: str | None = None


class TransportOffer(BaseOffer):
    kind: Literal[OfferKind.train, OfferKind.bus]
    operator: str
    service_number: str = Field(description="Train number or bus service id")
    service_name: str = ""
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    travel_class: str = ""
    seats_available: int | None = None
    amenities: list[str] = []


class ActivityOffer(BaseOffer):
    kind: Literal[OfferKind.activity] = OfferKind.activity
    product_code: str
    name: str
    description: str = ""
    duration_minutes: int | None = None
    rating: float | None = None
    review_count: int | None = None
    images: list[MediaImage] = []
    date: Date | None = None


AnyOffer = FlightOffer | HotelOffer | TransportOffer | ActivityOffer

OFFER_MODELS: dict[OfferKind, type[BaseOffer]] = {
    OfferKind.flight: FlightOffer,
    OfferKind.hotel: HotelOffer,
    OfferKind.train: TransportOffer,
    OfferKind.bus: TransportOffer,
    OfferKind.activity: ActivityOffer,
}


def parse_offer(data: dict) -> AnyOffer:
    return OFFER_MODELS[OfferKind(data["kind"])].model_validate(data)  # type: ignore[return-value]


# ─── Booking inputs passed to providers ───────────────────────────

class TravelerInfo(APIModel):
    type: PassengerType = PassengerType.adult
    title: Literal["mr", "ms", "mrs", "miss", "dr"] | None = None
    given_name: str = Field(min_length=1, max_length=60)
    family_name: str = Field(min_length=1, max_length=60)
    born_on: date | None = None
    gender: Literal["m", "f", "x"] | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20, examples=["+919876543210"])
    nationality: str | None = Field(default=None, min_length=2, max_length=2)
    passport_number: str | None = Field(default=None, max_length=20)
    passport_expiry: date | None = None


class ContactInfo(APIModel):
    email: EmailStr
    phone: str = Field(min_length=6, max_length=20)


class ProviderBookingResult(APIModel):
    provider_reference: str = Field(description="PNR / confirmation number")
    status: Literal["confirmed", "pending", "failed"]
    tickets: list[str] = []
    message: str = ""
    raw: dict = {}
