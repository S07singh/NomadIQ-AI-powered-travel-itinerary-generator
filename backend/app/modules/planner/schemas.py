"""
Planner schemas.

*Draft* models are what the LLM is asked to return (small, flat, no media fields,
so local models stay accurate). They are converted into the richer *output*
models, which are then enriched with images, videos, maps links, weather and a
computed budget.

Each draft defines `mock_example(prompt)` so the MockLLM returns realistic data
for offline development and tests.
"""

import re
from datetime import date, datetime
from datetime import date as Date
from typing import Literal

from pydantic import Field

from app.common.schemas import APIModel, MediaImage, Place, VideoLink, WeatherDay

TimeOfDay = Literal["morning", "afternoon", "evening", "night"]
ItemKind = Literal["activity", "meal", "transport", "rest", "hotel"]


def _marker(prompt: str, name: str, default: str = "") -> str:
    m = re.search(rf"^{name}:[ \t]*(.+)$", prompt, re.MULTILINE)
    return m.group(1).strip() if m else default


def _dest(prompt: str) -> str:
    return _marker(prompt, "DESTINATION", "the destination").split(",")[0].strip()


def _days(prompt: str) -> int:
    try:
        return max(1, min(30, int(_marker(prompt, "DAYS", "3"))))
    except ValueError:
        return 3


# ─── LLM drafts ───────────────────────────────────────────────────

class LocalInfo(APIModel):
    language: str = ""
    currency: str = ""
    timezone: str = ""
    emergency_numbers: list[str] = []
    best_time_to_visit: str = ""
    getting_around: str = ""
    etiquette: list[str] = []


class AttractionDraft(APIModel):
    name: str
    description: str = ""
    area: str = ""
    category: str = Field(default="", description="landmark | museum | nature | beach | market | temple | viewpoint | experience")
    estimated_cost: float | None = Field(default=None, description="Per person, in the trip currency; 0 if free")
    visit_duration_hours: float | None = None
    best_time: str = ""
    booking_required: bool = False


class DestinationDraft(APIModel):
    summary: str = ""
    highlights: list[str] = []
    attractions: list[AttractionDraft] = []
    local_info: LocalInfo = LocalInfo()
    packing_list: list[str] = []
    travel_tips: list[str] = []

    @classmethod
    def mock_example(cls, prompt: str) -> "DestinationDraft":
        d = _dest(prompt)
        cats = [("Old Fort", "landmark", 10), ("City Museum", "museum", 8), ("Sunset Point", "viewpoint", 0), ("Central Market", "market", 0), ("Riverside Park", "nature", 0), ("Heritage Temple", "temple", 2)]
        return cls(
            summary=f"{d} blends history, food and scenery — ideal for a relaxed yet varied trip.",
            highlights=[f"Sunset views over {d}", "Local street food", "Historic old town"],
            attractions=[
                AttractionDraft(name=f"{d} {n}", description=f"Popular {c} in {d}.", area="Central", category=c, estimated_cost=cost, visit_duration_hours=2, best_time="Morning", booking_required=c == "museum")
                for n, c, cost in cats
            ],
            local_info=LocalInfo(language="Local language & English", currency="Local currency", timezone="Local time", emergency_numbers=["112"], best_time_to_visit="October to March", getting_around="Taxis, ride-hailing apps and walking"),
            packing_list=["Comfortable walking shoes", "Sunscreen", "Reusable water bottle", "Power bank"],
            travel_tips=["Carry some cash for small vendors", "Start sightseeing early to avoid crowds"],
        )


class HotelDraft(APIModel):
    name: str
    area: str = ""
    description: str = ""
    price_per_night: float | None = Field(default=None, description="Per room per night, in the trip currency")
    rating: float | None = Field(default=None, ge=0, le=5)
    amenities: list[str] = []
    why: str = Field(default="", description="Why it fits this traveler")


class HotelsDraft(APIModel):
    hotels: list[HotelDraft] = []

    @classmethod
    def mock_example(cls, prompt: str) -> "HotelsDraft":
        d = _dest(prompt)
        return cls(hotels=[
            HotelDraft(name=f"{d} Budget Inn", area="Old Town", price_per_night=40, rating=3.6, amenities=["WiFi"], why="Cheapest well-rated option"),
            HotelDraft(name=f"{d} Comfort Suites", area="Central", price_per_night=95, rating=4.2, amenities=["WiFi", "Breakfast", "Pool"], why="Great location and value"),
            HotelDraft(name=f"Grand {d} Resort", area="Waterfront", price_per_night=240, rating=4.7, amenities=["Spa", "Pool", "Restaurant"], why="Luxury splurge"),
        ])


class RestaurantDraft(APIModel):
    name: str
    cuisine: str = ""
    area: str = ""
    description: str = ""
    price_level: int | None = Field(default=None, ge=1, le=4, description="1=cheap … 4=fine dining")
    avg_cost_per_person: float | None = None
    must_try: list[str] = []
    dietary_options: list[str] = []


class DiningDraft(APIModel):
    restaurants: list[RestaurantDraft] = []
    local_dishes: list[str] = []

    @classmethod
    def mock_example(cls, prompt: str) -> "DiningDraft":
        d = _dest(prompt)
        return cls(
            restaurants=[
                RestaurantDraft(name=f"{d} Street Food Lane", cuisine="Street food", area="Market", price_level=1, avg_cost_per_person=6, must_try=["Local snack platter"], dietary_options=["vegetarian"]),
                RestaurantDraft(name=f"Spice Route {d}", cuisine="Regional", area="Central", price_level=2, avg_cost_per_person=15, must_try=["House curry"], dietary_options=["vegetarian", "vegan"]),
                RestaurantDraft(name=f"The {d} Table", cuisine="Fine dining", area="Waterfront", price_level=4, avg_cost_per_person=55, must_try=["Tasting menu"]),
            ],
            local_dishes=["Regional thali", "Fresh seafood", "Local sweets"],
        )


class ItineraryItemDraft(APIModel):
    time_of_day: TimeOfDay = "morning"
    start_time: str | None = Field(default=None, description="24h HH:MM")
    title: str
    description: str = ""
    place_name: str = ""
    kind: ItemKind = "activity"
    estimated_cost: float | None = Field(default=None, description="Per person, trip currency")
    duration_hours: float | None = None


class DayDraft(APIModel):
    day: int = Field(ge=1)
    title: str = ""
    items: list[ItineraryItemDraft] = []
    notes: str = ""


class ItineraryDraft(APIModel):
    days: list[DayDraft] = []

    @classmethod
    def mock_example(cls, prompt: str) -> "ItineraryDraft":
        d, n = _dest(prompt), _days(prompt)
        places = [p.strip() for p in _marker(prompt, "ATTRACTIONS", "").split(";") if p.strip()] or [f"{d} Old Fort"]
        days = []
        for i in range(1, n + 1):
            p = places[(i - 1) % len(places)]
            days.append(DayDraft(day=i, title=f"Day {i} in {d}", notes="Carry water and start early.", items=[
                ItineraryItemDraft(time_of_day="morning", start_time="09:00", title=f"Visit {p}", place_name=p, kind="activity", estimated_cost=10, duration_hours=2.5),
                ItineraryItemDraft(time_of_day="afternoon", start_time="13:00", title="Lunch at a local favourite", place_name=f"Spice Route {d}", kind="meal", estimated_cost=15, duration_hours=1),
                ItineraryItemDraft(time_of_day="afternoon", start_time="15:00", title="Explore the old town", place_name=f"{d} Central Market", kind="activity", estimated_cost=0, duration_hours=2),
                ItineraryItemDraft(time_of_day="evening", start_time="19:30", title="Dinner and evening stroll", place_name=f"{d} Street Food Lane", kind="meal", estimated_cost=12, duration_hours=1.5),
            ]))
        return cls(days=days)


class TripEditDraft(APIModel):
    """LLM output for chat-based itinerary edits."""

    reply: str = Field(description="Short friendly message describing what changed")
    changed: bool = False
    days: list[DayDraft] | None = Field(default=None, description="The FULL updated list of days when changed=true")

    @classmethod
    def mock_example(cls, prompt: str) -> "TripEditDraft":
        request = _marker(prompt, "USER_REQUEST", "")
        n = _days(prompt)
        if not request or request.lower().startswith(("what", "how", "why", "when", "is ", "can you tell")):
            return cls(reply="Here's what I found — your plan is unchanged.", changed=False)
        base = ItineraryDraft.mock_example(prompt)
        if base.days:
            base.days[-1].items.append(ItineraryItemDraft(time_of_day="night", start_time="21:30", title=f"Added: {request[:60]}", kind="activity", estimated_cost=20, duration_hours=2))
        return cls(reply=f"Done! I updated your itinerary: {request[:80]}", changed=True, days=base.days[:n])


# ─── Output (stored on the trip, returned to clients) ─────────────

class Attraction(AttractionDraft):
    maps_url: str | None = None
    images: list[MediaImage] = []
    videos: list[VideoLink] = []


class HotelSuggestion(HotelDraft):
    maps_url: str | None = None
    images: list[MediaImage] = []
    search_hint: dict | None = Field(default=None, description="Prefilled body for POST /search/hotels to book live rates")


class RestaurantSuggestion(RestaurantDraft):
    maps_url: str | None = None
    images: list[MediaImage] = []


class ItineraryItem(ItineraryItemDraft):
    maps_url: str | None = None
    image: MediaImage | None = None


class DayPlan(APIModel):
    day: int
    date: Date | None = None
    title: str = ""
    items: list[ItineraryItem] = []
    notes: str = ""
    weather: WeatherDay | None = None


class BudgetLine(APIModel):
    category: Literal["accommodation", "food", "activities", "local_transport", "misc"]
    amount: float
    note: str = ""


class BudgetBreakdown(APIModel):
    currency: str
    total: float
    per_person: float
    per_day: float
    lines: list[BudgetLine]
    budget_limit: float | None = None
    within_budget: bool | None = None
    tips: list[str] = []


class TripPlan(APIModel):
    summary: str = ""
    highlights: list[str] = []
    location: Place | None = None
    cover_image: MediaImage | None = None
    gallery: list[MediaImage] = []
    videos: list[VideoLink] = []
    days: list[DayPlan] = []
    attractions: list[Attraction] = []
    hotels: list[HotelSuggestion] = []
    restaurants: list[RestaurantSuggestion] = []
    local_dishes: list[str] = []
    budget: BudgetBreakdown | None = None
    local_info: LocalInfo | None = None
    packing_list: list[str] = []
    travel_tips: list[str] = []
    weather: list[WeatherDay] = []
    generated_at: datetime | None = None
    generation_ms: int | None = None
    ai_model: str | None = None
