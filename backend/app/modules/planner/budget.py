"""
Deterministic budget calculation from the generated plan.

Computed in code (not by the LLM) because it is instant, reproducible and the
arithmetic is always right. LLM-provided per-item estimates feed into it.
"""

import math
import statistics

from app.common.fx import from_usd
from app.modules.planner.schemas import BudgetBreakdown, BudgetLine, TripPlan
from app.modules.trips.schemas import TripInputs

# Fallback daily estimates in USD, used when the plan lacks prices.
HOTEL_PER_NIGHT_USD = {"backpacker": 20, "budget": 45, "comfort": 110, "luxury": 320}
FOOD_PER_PERSON_DAY_USD = {"backpacker": 12, "budget": 20, "comfort": 40, "luxury": 110}
TRANSPORT_PER_DAY_USD = {"backpacker": 5, "budget": 10, "comfort": 25, "luxury": 70}
MISC_RATE = 0.08


def _pick_hotel_price(prices: list[float], style: str) -> float:
    prices = sorted(prices)
    if style in ("backpacker", "budget"):
        return prices[0]
    if style == "luxury":
        return prices[-1]
    return statistics.median(prices)


def compute_budget(plan: TripPlan, t: TripInputs) -> BudgetBreakdown:
    cur = t.currency
    style = t.travel_style.value
    days = t.duration_days or max(len(plan.days), 1)
    nights = max(days - 1, 1)
    paying = t.travelers.adults + t.travelers.children
    rooms = max(1, math.ceil(t.travelers.adults / 2))

    prices = [h.price_per_night for h in plan.hotels if h.price_per_night]
    per_night = _pick_hotel_price(prices, style) if prices else from_usd(HOTEL_PER_NIGHT_USD[style], cur)
    accommodation = per_night * nights * rooms

    items = [i for d in plan.days for i in d.items]
    activity_pp = sum(i.estimated_cost or 0 for i in items if i.kind == "activity")
    meal_pp = sum(i.estimated_cost or 0 for i in items if i.kind == "meal")
    activities = activity_pp * paying
    food_floor = from_usd(FOOD_PER_PERSON_DAY_USD[style], cur) * days * paying
    food = max(meal_pp * paying, food_floor * 0.6) if meal_pp else food_floor
    transport_pp = sum(i.estimated_cost or 0 for i in items if i.kind == "transport")
    local_transport = max(transport_pp * paying, from_usd(TRANSPORT_PER_DAY_USD[style], cur) * days)

    subtotal = accommodation + food + activities + local_transport
    misc = subtotal * MISC_RATE
    total = round(subtotal + misc, 2)

    lines = [
        BudgetLine(category="accommodation", amount=round(accommodation, 2), note=f"{nights} night(s) × {rooms} room(s) at ~{per_night:,.0f} {cur}"),
        BudgetLine(category="food", amount=round(food, 2), note=f"{paying} traveler(s) × {days} day(s)"),
        BudgetLine(category="activities", amount=round(activities, 2), note="Entry fees and experiences in the itinerary"),
        BudgetLine(category="local_transport", amount=round(local_transport, 2), note="Taxis, metro, rentals"),
        BudgetLine(category="misc", amount=round(misc, 2), note=f"{int(MISC_RATE * 100)}% buffer for tips, SIM, shopping"),
    ]
    limit = t.budget.amount if t.budget else None
    within = (total <= limit) if limit else None
    tips: list[str] = []
    if limit and not within:
        over = total - limit
        tips.append(f"Estimated cost is {over:,.0f} {cur} over budget.")
        if style in ("comfort", "luxury"):
            tips.append("Switching to a cheaper stay saves the most — accommodation is usually the biggest line.")
        tips.append("Swap one paid activity per day for free sights or walking tours.")
        tips.append("Eat at local eateries and street food stalls for most meals.")
    elif limit:
        tips.append(f"You have ~{limit - total:,.0f} {cur} left for shopping or upgrades.")
    tips.append("Flights/trains to the destination are not included — search them in the app to add live prices.")

    return BudgetBreakdown(
        currency=cur,
        total=total,
        per_person=round(total / max(paying, 1), 2),
        per_day=round(total / days, 2),
        lines=lines,
        budget_limit=limit,
        within_budget=within,
        tips=tips,
    )
