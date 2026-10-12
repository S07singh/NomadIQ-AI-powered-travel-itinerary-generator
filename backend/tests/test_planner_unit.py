from datetime import date, timedelta

import pytest
from bson import ObjectId

from app.core.exceptions import ProviderError
from app.modules.planner.agents import normalise_days, trip_brief
from app.modules.planner.budget import compute_budget
from app.modules.planner.orchestrator import TripPlanner
from app.modules.planner.schemas import (
    DayDraft,
    DestinationDraft,
    HotelsDraft,
    HotelSuggestion,
    ItineraryDraft,
    ItineraryItem,
    DayPlan,
    TripPlan,
)
from app.modules.trips.schemas import TripInputs
from app.providers.llm import LLMProvider, MockLLM, extract_json


def test_extract_json_handles_fences_and_chatter():
    assert extract_json('Sure! ```json\n{"a": 1}\n``` hope that helps') == '{"a": 1}'
    assert extract_json('noise [1, 2] tail') == "[1, 2]"
    assert extract_json('{bad} then {"ok": true}') == '{"ok": true}'


def test_normalise_days_fills_and_dedupes():
    draft = ItineraryDraft(days=[DayDraft(day=1, title="a"), DayDraft(day=1, title="dup"), DayDraft(day=7, title="far")])
    days = normalise_days(draft, 3).days
    assert [d.day for d in days] == [1, 2, 3]
    assert days[0].title == "a"
    assert days[1].title in ("dup", "far")


def test_trip_inputs_brief_contains_markers():
    t = TripInputs(destination="Goa", duration_days=4, additional_info="vegetarian please")
    brief = trip_brief(t)
    assert "DESTINATION: Goa" in brief and "DAYS: 4" in brief and 'TRAVELER_NOTES: "vegetarian please"' in brief


def _plan(prices, item_cost):
    return TripPlan(
        hotels=[HotelSuggestion(name=f"h{i}", price_per_night=p) for i, p in enumerate(prices)],
        days=[DayPlan(day=i, items=[ItineraryItem(title="x", kind="activity", estimated_cost=item_cost), ItineraryItem(title="m", kind="meal", estimated_cost=10)]) for i in (1, 2, 3)],
    )


def test_budget_math_and_style_choice():
    t = TripInputs(destination="Goa", duration_days=3, travelers={"adults": 2}, budget={"amount": 100000, "currency": "INR"}, travel_style="luxury")
    b = compute_budget(_plan([1000, 3000, 9000], 50), t)
    acc = next(line for line in b.lines if line.category == "accommodation")
    assert acc.amount == 9000 * 2 * 1  # luxury picks the priciest, 2 nights, 1 room
    acts = next(line for line in b.lines if line.category == "activities")
    assert acts.amount == 50 * 3 * 2
    assert b.total == pytest.approx(sum(line.amount for line in b.lines), abs=0.05)
    assert b.within_budget is True and b.per_person == pytest.approx(b.total / 2, abs=0.01)


def test_budget_over_limit_gives_tips_and_fallback_prices():
    t = TripInputs(destination="Goa", duration_days=3, budget={"amount": 10, "currency": "USD"}, travel_style="comfort")
    b = compute_budget(TripPlan(), t)
    assert b.within_budget is False
    assert any("over budget" in tip for tip in b.tips)
    assert b.lines[0].amount > 0  # fallback hotel estimate used


class FlakyLLM(LLMProvider):
    name = "flaky"

    def __init__(self, outputs):
        self.outputs = list(outputs)

    async def generate(self, prompt, system="", temperature=0.7):
        return ""

    async def _generate_json_text(self, prompt, system, schema, temperature):
        return self.outputs.pop(0)


async def test_generate_json_retries_then_succeeds():
    llm = FlakyLLM(["not json at all", '```json\n{"hotels": [{"name": "Taj"}]}\n```'])
    result = await llm.generate_json("p", HotelsDraft)
    assert result.hotels[0].name == "Taj"


async def test_generate_json_raises_after_retries():
    llm = FlakyLLM(["nope", '{"hotels": "wrong-type"}'])
    with pytest.raises(ProviderError) as exc:
        await llm.generate_json("p", HotelsDraft)
    assert exc.value.code == "llm_invalid_output"


class PartialLLM(MockLLM):
    """Hotel agent fails; everything else works."""

    def __init__(self, fail_schema):
        self.fail_schema = fail_schema

    async def generate_json(self, prompt, schema, system="", temperature=0.3, retries=1):
        if schema is self.fail_schema:
            raise ProviderError("boom")
        return await super().generate_json(prompt, schema, system, temperature, retries)


async def _run_planner(db, providers, settings, llm):
    start = date.today() + timedelta(days=2)
    doc = {**TripInputs(destination="Jaipur", start_date=start, duration_days=2).model_dump(mode="json"), "status": "queued", "progress": {}, "user_id": ObjectId()}
    trip_id = (await db["trips"].insert_one(doc)).inserted_id
    original = providers.llm
    providers.llm = llm
    try:
        await TripPlanner(db, providers, settings).run(trip_id)
    finally:
        providers.llm = original
    return await db["trips"].find_one({"_id": trip_id})


async def test_planner_degrades_when_hotel_agent_fails(app, db, providers):
    doc = await _run_planner(db, providers, app.state.settings, PartialLLM(HotelsDraft))
    assert doc["status"] == "ready"
    assert doc["plan"]["hotels"] == [] and len(doc["plan"]["days"]) == 2


async def test_planner_fails_when_destination_agent_fails(app, db, providers):
    doc = await _run_planner(db, providers, app.state.settings, PartialLLM(DestinationDraft))
    assert doc["status"] == "failed" and doc["error"] == "boom"
