from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from app.common.schemas import APIModel, MediaImage, TravelStyle, TripPace, Vibe
from app.modules.planner.schemas import TripPlan

MAX_TRIP_DAYS = 30


class TripStatus(StrEnum):
    draft = "draft"
    queued = "queued"
    generating = "generating"
    ready = "ready"
    failed = "failed"


class TravelerCount(APIModel):
    adults: int = Field(default=1, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=10)
    infants: int = Field(default=0, ge=0, le=5)

    @property
    def total(self) -> int:
        return self.adults + self.children + self.infants


class TripBudget(APIModel):
    amount: float = Field(gt=0, description="Total budget for the whole group and trip")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    flexible: bool = False


class TripInputs(APIModel):
    """Everything the planner needs. Shared by create / update / stored trip."""

    title: str | None = Field(default=None, max_length=120)
    destination: str = Field(min_length=2, max_length=120, examples=["Goa, India"])
    origin: str | None = Field(default=None, max_length=120, examples=["Bengaluru"])
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1, le=MAX_TRIP_DAYS)
    travelers: TravelerCount = TravelerCount()
    budget: TripBudget | None = None
    travel_style: TravelStyle = TravelStyle.comfort
    pace: TripPace = TripPace.moderate
    vibes: list[Vibe] = Field(default_factory=list, max_length=8)
    interests: list[str] = Field(default_factory=list, max_length=20)
    dietary: list[str] = Field(default_factory=list, max_length=10)
    additional_info: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _normalise_dates(self) -> "TripInputs":
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date")
            span = (self.end_date - self.start_date).days + 1
            if span > MAX_TRIP_DAYS:
                raise ValueError(f"trips can be at most {MAX_TRIP_DAYS} days")
            self.duration_days = span
        elif self.start_date:
            self.duration_days = self.duration_days or 3
            self.end_date = self.start_date + timedelta(days=self.duration_days - 1)
        elif self.end_date:
            raise ValueError("start_date is required when end_date is given")
        else:
            self.duration_days = self.duration_days or 3
        if not self.title:
            self.title = f"Trip to {self.destination.split(',')[0].strip()}"
        return self

    @property
    def currency(self) -> str:
        return self.budget.currency.upper() if self.budget else "USD"


class TripCreate(TripInputs):
    generate: bool = Field(default=True, description="Start AI generation immediately")


class TripUpdate(APIModel):
    """Partial update of trip inputs. Call POST /trips/{id}/generate to re-plan."""

    title: str | None = Field(default=None, max_length=120)
    destination: str | None = Field(default=None, min_length=2, max_length=120)
    origin: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1, le=MAX_TRIP_DAYS)
    travelers: TravelerCount | None = None
    budget: TripBudget | None = None
    travel_style: TravelStyle | None = None
    pace: TripPace | None = None
    vibes: list[Vibe] | None = Field(default=None, max_length=8)
    interests: list[str] | None = Field(default=None, max_length=20)
    dietary: list[str] | None = Field(default=None, max_length=10)
    additional_info: str | None = Field(default=None, max_length=2000)


class TripProgress(APIModel):
    status: TripStatus
    step: str = ""
    percent: int = Field(default=0, ge=0, le=100)
    message: str = ""
    updated_at: datetime | None = None


class TripSummary(APIModel):
    id: str
    title: str
    destination: str
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int
    status: TripStatus
    travel_style: TravelStyle
    cover_image: MediaImage | None = None
    created_at: datetime
    updated_at: datetime


class TripOut(TripInputs):
    id: str
    status: TripStatus
    progress: TripProgress
    plan: TripPlan | None = None
    plan_version: int = 0
    error: str | None = None
    is_shared: bool = False
    created_at: datetime
    updated_at: datetime


class TripChatRequest(APIModel):
    message: str = Field(min_length=1, max_length=1000, examples=["Make day 2 more adventurous"])


class TripMessage(APIModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    plan_version: int | None = None
    created_at: datetime


class TripChatResponse(APIModel):
    reply: TripMessage
    plan_updated: bool
    trip: TripOut


class ShareResponse(APIModel):
    share_token: str
    share_url: str
