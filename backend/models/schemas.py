"""
Pydantic models for NomadIQ API requests, responses, and structured AI output.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ─── Trip Planning Request (from frontend form) ───────────────────

class TravelDates(BaseModel):
    start: str = ""
    end: str = ""


class TravelPlanRequest(BaseModel):
    """User input from the trip planning form."""
    name: str = ""
    destination: str = ""
    starting_location: str = ""
    travel_dates: TravelDates = TravelDates()
    duration: int = 3
    traveling_with: str = "Solo"
    adults: int = 1
    children: int = 0
    budget: float = 1000
    budget_currency: str = "USD"
    travel_style: str = "comfort"
    budget_flexible: bool = False
    vibes: List[str] = []
    interests: str = ""
    rooms: int = 1
    pace: List[int] = [3]
    additional_info: str = ""


class TriggerPlanRequest(BaseModel):
    """Wrapper for triggering plan generation."""
    trip_plan_id: str
    travel_plan: TravelPlanRequest


class TriggerPlanResponse(BaseModel):
    """Response after triggering plan generation."""
    success: bool
    message: str
    trip_plan_id: str


# ─── Structured AI Output (what agents produce) ──────────────────

class DayPlan(BaseModel):
    day: int = Field(default=1, description="Day number")
    date: str = Field(default="", description="Date string")
    morning: str = Field(default="", description="Morning activities")
    afternoon: str = Field(default="", description="Afternoon activities")
    evening: str = Field(default="", description="Evening activities")
    notes: str = Field(default="", description="Tips for the day")


class HotelResult(BaseModel):
    hotel_name: str = Field(default="", description="Hotel name")
    price: str = Field(default="", description="Price per night")
    rating: str = Field(default="", description="Rating out of 5")
    address: str = Field(default="", description="Hotel address")
    amenities: List[str] = Field(default_factory=list, description="Amenities")
    description: str = Field(default="", description="Short description")


class FlightResult(BaseModel):
    airline: str = Field(default="", description="Airline name")
    price: str = Field(default="", description="Ticket price")
    departure_time: str = Field(default="", description="Departure time")
    arrival_time: str = Field(default="", description="Arrival time")
    duration: str = Field(default="", description="Flight duration")
    stops: int = Field(default=0, description="Number of stops")


class AttractionResult(BaseModel):
    name: str = Field(default="", description="Attraction name")
    description: str = Field(default="", description="Description")
    location: str = Field(default="", description="Location/area")
    estimated_cost: str = Field(default="Free", description="Cost estimate")
    visit_duration: str = Field(default="1-2 hours", description="Suggested visit time")


class RestaurantResult(BaseModel):
    name: str = Field(default="", description="Restaurant name")
    cuisine: str = Field(default="", description="Cuisine type")
    price_range: str = Field(default="", description="Price range ($, $$, $$$)")
    description: str = Field(default="", description="Short description")
    location: str = Field(default="", description="Location")


class ItineraryResponse(BaseModel):
    """Complete structured itinerary from the AI agents."""
    day_by_day_plan: List[DayPlan] = Field(default_factory=list)
    hotels: List[HotelResult] = Field(default_factory=list)
    flights: List[FlightResult] = Field(default_factory=list)
    attractions: List[AttractionResult] = Field(default_factory=list)
    restaurants: List[RestaurantResult] = Field(default_factory=list)
    budget_summary: str = Field(default="", description="Budget analysis text")
    tips: List[str] = Field(default_factory=list)
    total_estimated_cost: str = Field(default="", description="Total trip cost estimate")


# ─── Chat Modification ────────────────────────────────────────────

class ChatRequest(BaseModel):
    """User message to modify an existing itinerary."""
    trip_plan_id: str
    message: str


class ChatResponse(BaseModel):
    """AI response after modifying the itinerary."""
    success: bool
    message: str
    updated_itinerary: Optional[str] = None


# ─── Plan Status ──────────────────────────────────────────────────

class PlanStatusResponse(BaseModel):
    """Status of a trip plan generation."""
    trip_plan_id: str
    status: str  # pending, processing, completed, failed
    current_step: Optional[str] = None
    itinerary: Optional[str] = None  # JSON string of ItineraryResponse
    error: Optional[str] = None
    created_at: Optional[str] = None
