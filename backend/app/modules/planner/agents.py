"""
Planner agents. Each agent = one focused prompt + one structured LLM call.
Destination, hotel and dining agents are independent and run in parallel;
the itinerary agent then composes their output.
"""

from app.modules.planner.schemas import (
    DayDraft,
    DestinationDraft,
    DiningDraft,
    HotelsDraft,
    ItineraryDraft,
    TripEditDraft,
)
from app.modules.trips.schemas import TripInputs
from app.providers.llm import LLMProvider

PACE_ITEMS = {"relaxed": "2-3", "moderate": "3-4", "packed": "4-6"}


def trip_brief(t: TripInputs) -> str:
    """Compact, marker-style brief. Markers (KEY: value) keep small models on track."""
    budget = f"{t.budget.amount:g} {t.budget.currency} total for the group ({'flexible' if t.budget.flexible else 'strict'})" if t.budget else "not specified"
    dates = f"{t.start_date} to {t.end_date}" if t.start_date else "flexible"
    lines = [
        f"DESTINATION: {t.destination}",
        f"DAYS: {t.duration_days}",
        f"DATES: {dates}",
        f"ORIGIN: {t.origin or 'not specified'}",
        f"TRAVELERS: {t.travelers.adults} adults, {t.travelers.children} children, {t.travelers.infants} infants",
        f"BUDGET: {budget}",
        f"CURRENCY: {t.currency}",
        f"STYLE: {t.travel_style.value}",
        f"PACE: {t.pace.value}",
        f"VIBES: {', '.join(v.value for v in t.vibes) or 'any'}",
        f"INTERESTS: {', '.join(t.interests) or 'any'}",
        f"DIETARY: {', '.join(t.dietary) or 'none'}",
    ]
    if t.additional_info:
        lines.append(f'TRAVELER_NOTES: "{t.additional_info[:600]}"')
    return "\n".join(lines)


async def destination_agent(llm: LLMProvider, t: TripInputs) -> DestinationDraft:
    prompt = (
        f"{trip_brief(t)}\n\n"
        f"Research {t.destination} for this traveler. Return a 2-3 sentence summary, 3-5 highlights, "
        f"6-10 real attractions matching their vibes/interests (mix famous sights and hidden gems), "
        f"local practical info, a short packing list for the season and 3-6 travel tips. "
        f"All costs per person in {t.currency}. Use real place names only."
    )
    return await llm.generate_json(prompt, DestinationDraft, system="You are an expert local travel researcher.", temperature=0.6)


async def hotel_agent(llm: LLMProvider, t: TripInputs) -> HotelsDraft:
    prompt = (
        f"{trip_brief(t)}\n\n"
        f"Recommend 3-5 real hotels or stays in {t.destination} that fit the {t.travel_style.value} style and budget, "
        f"spread across price points and good neighbourhoods. price_per_night is per room in {t.currency}."
    )
    return await llm.generate_json(prompt, HotelsDraft, system="You are a hotel expert who knows real properties.", temperature=0.4)


async def dining_agent(llm: LLMProvider, t: TripInputs) -> DiningDraft:
    prompt = (
        f"{trip_brief(t)}\n\n"
        f"Recommend 4-6 real restaurants/food spots in {t.destination} (include street food and one special-occasion place) "
        f"respecting dietary needs, plus 3-6 local dishes to try. avg_cost_per_person in {t.currency}."
    )
    return await llm.generate_json(prompt, DiningDraft, system="You are a local food guide.", temperature=0.6)


async def itinerary_agent(llm: LLMProvider, t: TripInputs, dest: DestinationDraft, hotels: HotelsDraft, dining: DiningDraft) -> ItineraryDraft:
    attractions = "; ".join(a.name for a in dest.attractions[:12])
    restaurants = "; ".join(r.name for r in dining.restaurants[:8])
    prompt = (
        f"{trip_brief(t)}\n"
        f"ATTRACTIONS: {attractions}\n"
        f"RESTAURANTS: {restaurants}\n"
        f"HOTEL_AREA: {hotels.hotels[0].area if hotels.hotels else 'central'}\n\n"
        f"Create a day-by-day itinerary with EXACTLY {t.duration_days} days (day 1..{t.duration_days}). "
        f"Each day has {PACE_ITEMS[t.pace.value]} activities plus meals, grouped by nearby areas to minimise travel, "
        f"with realistic start_time values. Use the attractions and restaurants above where sensible. "
        f"Day 1 should allow for arrival; the last day for departure. estimated_cost per person in {t.currency}."
    )
    draft = await llm.generate_json(prompt, ItineraryDraft, system="You are a meticulous travel itinerary planner.", temperature=0.5)
    return normalise_days(draft, t.duration_days)


def normalise_days(draft: ItineraryDraft, n: int) -> ItineraryDraft:
    """Guarantee exactly n days numbered 1..n (small models often skip or duplicate days)."""
    by_day: dict[int, DayDraft] = {}
    for d in draft.days:
        if 1 <= d.day <= n and d.day not in by_day:
            by_day[d.day] = d
    leftovers = [d for d in draft.days if d not in by_day.values()]
    days = []
    for i in range(1, n + 1):
        day = by_day.get(i) or (leftovers.pop(0) if leftovers else DayDraft(day=i, title=f"Day {i}: free exploration", notes="Flexible day — explore at your own pace."))
        day.day = i
        days.append(day)
    return ItineraryDraft(days=days)


async def edit_agent(llm: LLMProvider, t: TripInputs, days_json: str, request: str, history: str) -> TripEditDraft:
    prompt = (
        f"{trip_brief(t)}\n"
        f'USER_REQUEST: {request}\n\n'
        f"RECENT_CHAT:\n{history or '(none)'}\n\n"
        f"CURRENT_DAYS_JSON: {days_json}\n\n"
        "If the user asks a question, answer it in `reply` and set changed=false. "
        "If they want changes, apply ONLY what they asked, keep everything else identical, set changed=true "
        f"and return the FULL list of {t.duration_days} days."
    )
    return await llm.generate_json(prompt, TripEditDraft, system="You are a helpful travel planner editing an existing itinerary.", temperature=0.3)
