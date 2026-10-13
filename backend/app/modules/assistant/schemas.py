import re
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from app.common.schemas import APIModel


class AssistantIntent(StrEnum):
    chat = "chat"
    plan_trip = "plan_trip"
    search_flights = "search_flights"
    search_hotels = "search_hotels"
    search_trains = "search_trains"
    search_buses = "search_buses"
    search_activities = "search_activities"
    book_offer = "book_offer"
    modify_trip = "modify_trip"


def _marker(prompt: str, name: str) -> str:
    m = re.search(rf"^{name}:[ \t]*(.*)$", prompt, re.MULTILINE)
    return m.group(1).strip() if m else ""


class AssistantDecision(APIModel):
    """What the LLM returns: the user's intent, a reply and extracted parameters."""

    intent: AssistantIntent = AssistantIntent.chat
    reply: str = Field(default="", description="Short, friendly reply to show/speak to the user")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters for the intent, using the documented field names")
    missing: list[str] = Field(default_factory=list, description="Required info the user has not given yet")

    @classmethod
    def mock_example(cls, prompt: str) -> "AssistantDecision":
        msg = _marker(prompt, "USER_MESSAGE").lower()
        soon = date.today() + timedelta(days=30)
        if "book" in msg:
            return cls(intent=AssistantIntent.book_offer, reply="Sure — I'll hold that price for you.", params={"offer_id": _marker(prompt, "SELECTED_OFFER_ID") or None})
        if "flight" in msg:
            return cls(intent=AssistantIntent.search_flights, reply="Here are flights I found.", params={"origin": "DEL", "destination": "BOM", "departure_date": soon.isoformat()})
        if "hotel" in msg:
            return cls(intent=AssistantIntent.search_hotels, reply="Here are some stays.", params={"city": "Goa", "check_in": soon.isoformat(), "check_out": (soon + timedelta(days=3)).isoformat()})
        if "train" in msg:
            return cls(intent=AssistantIntent.search_trains, reply="Here are trains.", params={"origin": "New Delhi", "destination": "Jaipur", "date": soon.isoformat()})
        if "bus" in msg:
            return cls(intent=AssistantIntent.search_buses, reply="Here are buses.", params={"origin": "Bengaluru", "destination": "Goa", "date": soon.isoformat()})
        if "tour" in msg or "activit" in msg:
            return cls(intent=AssistantIntent.search_activities, reply="Here are things to do.", params={"destination": "Goa"})
        if _marker(prompt, "TRIP_ID") not in ("", "none") and any(w in msg for w in ("change", "add", "make", "replace", "remove")):
            return cls(intent=AssistantIntent.modify_trip, reply="Updating your trip.", params={"request": msg})
        if "plan" in msg or "trip to" in msg:
            dest = re.search(r"to ([a-z ]+?)(?: for| in|$)", msg)
            days = re.search(r"(\d+)\s*day", msg)
            return cls(intent=AssistantIntent.plan_trip, reply="Planning your trip now!", params={"destination": (dest.group(1).strip().title() if dest else "Goa"), "duration_days": int(days.group(1)) if days else 3})
        return cls(intent=AssistantIntent.chat, reply="I can plan trips, find flights, trains, buses, hotels and activities, and book them for you. Where would you like to go?")


class AssistantMessageRequest(APIModel):
    message: str = Field(min_length=1, max_length=2000, examples=["Find me a flight from Delhi to Mumbai next Friday"])
    conversation_id: str | None = None
    trip_id: str | None = Field(default=None, description="Trip the user is currently looking at")
    selected_offer_id: str | None = Field(default=None, description="Offer currently selected in the UI (for 'book this')")


ActionType = Literal["show_offers", "trip_created", "trip_updated", "booking_quote", "needs_info"]


class AssistantAction(APIModel):
    type: ActionType
    data: dict[str, Any] = {}


class AssistantMessage(APIModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    intent: AssistantIntent | None = None
    actions: list[AssistantAction] = []
    created_at: datetime


class AssistantReply(APIModel):
    conversation_id: str
    message: AssistantMessage
    transcript: str | None = Field(default=None, description="Present when the input was voice")


class ConversationSummary(APIModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
