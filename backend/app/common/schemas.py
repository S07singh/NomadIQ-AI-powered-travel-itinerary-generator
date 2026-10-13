"""Generic API schemas shared by every module."""

from datetime import date, datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class Page(APIModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    has_more: bool


class Money(APIModel):
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3, examples=["USD", "INR"])


class MessageResponse(APIModel):
    message: str


class ErrorDetail(APIModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(APIModel):
    error: ErrorDetail


# ─── Shared enums ─────────────────────────────────────────────────

class TravelStyle(StrEnum):
    backpacker = "backpacker"
    budget = "budget"
    comfort = "comfort"
    luxury = "luxury"


class TripPace(StrEnum):
    relaxed = "relaxed"
    moderate = "moderate"
    packed = "packed"


class Vibe(StrEnum):
    adventure = "adventure"
    relaxation = "relaxation"
    culture = "culture"
    food = "food"
    nightlife = "nightlife"
    nature = "nature"
    romance = "romance"
    family = "family"
    shopping = "shopping"
    spiritual = "spiritual"
    photography = "photography"


# ─── Media / places (used by planner, explore, search) ────────────

class MediaImage(APIModel):
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt: str = ""
    attribution: str = ""
    source: str = ""
    source_url: str | None = None


class VideoLink(APIModel):
    title: str
    url: str
    thumbnail_url: str | None = None
    channel: str | None = None
    source: str = "youtube"


class GeoPoint(APIModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class Place(APIModel):
    name: str
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    lat: float
    lng: float
    timezone: str | None = None
    population: int | None = None


class WeatherCode(StrEnum):
    clear = "clear"
    partly_cloudy = "partly_cloudy"
    cloudy = "cloudy"
    fog = "fog"
    drizzle = "drizzle"
    rain = "rain"
    snow = "snow"
    storm = "storm"
    unknown = "unknown"


class WeatherDay(APIModel):
    date: date
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    precipitation_mm: float | None = None
    precipitation_probability: int | None = None
    condition: WeatherCode = WeatherCode.unknown
    sunrise: datetime | str | None = None
    sunset: datetime | str | None = None
