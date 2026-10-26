"""Web-search grounding, plan flights, booking links, and the providers behind them."""

import json
from datetime import date, timedelta
from types import SimpleNamespace

import httpx
import pytest

from app.common.travel import FlightSearchRequest
from app.providers import airports
from app.providers.google_flights import GoogleFlightsProvider
from app.providers.llm import OpenRouterLLM
from app.providers.search import ExaSearch, MockWebSearch, NoWebSearch, TavilySearch
from app.modules.planner.schemas import HotelsDraft
from app.modules.search.service import OfferStore
from tests.conftest import future, wait_for_trip

TRIP = {
    "destination": "Jaipur, India",
    "origin": "Bengaluru",
    "travelers": {"adults": 2, "children": 0, "infants": 0},
    "budget": {"amount": 90000, "currency": "INR"},
}


@pytest.fixture
def grounded(providers):
    original = providers.search
    providers.search = MockWebSearch()
    yield providers
    providers.search = original


async def test_plan_is_grounded_in_web_results(app, client, auth, grounded):
    resp = await client.post("/trips", json={**TRIP, "start_date": future(10), "end_date": future(13)}, headers=auth["headers"])
    trip = await wait_for_trip(app, client, auth["headers"], resp.json()["id"])
    assert trip["status"] == "ready", trip.get("error")
    plan = trip["plan"]

    source_urls = {s["url"] for s in plan["sources"]}
    assert source_urls and all(u.startswith("https://example.com/") for u in source_urls)
    cited = [a["source_url"] for a in plan["attractions"] if a["source_url"]]
    assert cited and set(cited) <= source_urls
    # The mock model invents one URL; it must have been removed, not shown to users.
    assert plan["attractions"][-1]["source_url"] is None
    assert all(r["source_url"] in source_urls for r in plan["restaurants"])


async def test_plan_without_search_has_no_sources(app, client, auth):
    resp = await client.post("/trips", json={"destination": "Goa"}, headers=auth["headers"])
    plan = (await wait_for_trip(app, client, auth["headers"], resp.json()["id"]))["plan"]
    assert plan["sources"] == []
    assert all(a["source_url"] is None for a in plan["attractions"])


async def test_plan_includes_flights_links_and_budget_line(app, client, auth):
    resp = await client.post("/trips", json={**TRIP, "start_date": future(10), "end_date": future(13)}, headers=auth["headers"])
    plan = (await wait_for_trip(app, client, auth["headers"], resp.json()["id"]))["plan"]
    flights = plan["flights"]
    assert flights["origin_airport"]["iata_code"] == "BLR"
    assert flights["destination_airport"]["iata_code"] == "JAI"
    assert flights["outbound"] and flights["inbound"]
    assert flights["outbound"][0]["slices"][0]["origin"] == "BLR"
    assert flights["inbound"][0]["slices"][0]["origin"] == "JAI"
    labels = {link["label"] for link in flights["links"]}
    assert labels == {"Google Flights", "Kayak"}
    assert "BLR" in flights["links"][1]["url"] and future(10) in flights["links"][1]["url"]

    lines = {line["category"]: line for line in plan["budget"]["lines"]}
    cheapest = min(o["price"]["amount"] for o in flights["outbound"]) + min(o["price"]["amount"] for o in flights["inbound"])
    assert lines["flights"]["amount"] == pytest.approx(cheapest, abs=0.05)

    hotel = plan["hotels"][0]
    assert [link["label"] for link in hotel["links"]] == ["Booking.com", "Google Hotels", "Kayak"]
    assert f"checkin={future(10)}" in hotel["links"][0]["url"]

    # Flight offers from a plan are bookable straight away (they're in the offer store).
    offer = await client.get(f"/search/offers/{flights['outbound'][0]['offer_id']}", headers=auth["headers"])
    assert offer.status_code == 200


async def test_no_flights_without_origin_or_dates(app, client, auth):
    resp = await client.post("/trips", json={"destination": "Jaipur", "start_date": future(5)}, headers=auth["headers"])
    plan = (await wait_for_trip(app, client, auth["headers"], resp.json()["id"]))["plan"]
    assert plan["flights"] is None
    assert "flights" not in {line["category"] for line in plan["budget"]["lines"]}


async def test_external_offers_cannot_be_booked_in_app(client, auth, db, app):
    from app.common.schemas import Money
    from app.common.travel import FlightOffer

    store = OfferStore(db, 30)
    offer = FlightOffer(offer_id="google_flights:abc", provider="google_flights", title="IndiGo BLR→JAI", price=Money(amount=9000, currency="INR"),
                        bookable=False, deep_link="https://www.google.com/travel/flights/search?tfs=x", slices=[], passengers=1)
    await store.save_many([offer])
    resp = await client.post("/bookings", json={"offer_id": offer.offer_id, "travelers": [{"given_name": "A", "family_name": "B"}], "contact": {"email": "a@b.co", "phone": "+911234567"}}, headers=auth["headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "external_booking"
    assert resp.json()["error"]["details"]["deep_link"].startswith("https://www.google.com/travel/flights")


# ─── Providers ────────────────────────────────────────────────────

def client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_tavily_request_and_parse():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer tvly-key"
        body = json.loads(request.content)
        assert body["query"] == "best things to do in Jaipur" and body["max_results"] == 5
        return httpx.Response(200, json={"results": [{"title": "Amber Fort guide", "url": "https://t.example/amber", "content": "Go early." * 200}, {"title": "no url"}]})

    async with client_for(handler) as http:
        results = await TavilySearch(http, "tvly-key").search("best things to do in Jaipur", 5)
    assert [r.url for r in results] == ["https://t.example/amber"]
    assert len(results[0].snippet) <= 600
    async with client_for(lambda r: httpx.Response(500)) as http:
        assert await TavilySearch(http, "tvly-key").search("x") == []


async def test_exa_request_and_parse():
    def handler(request):
        assert request.headers["x-api-key"] == "exa-key"
        body = json.loads(request.content)
        assert body["numResults"] == 3 and body["contents"] == {"highlights": True}
        return httpx.Response(200, json={"results": [{"title": "Hawa Mahal", "url": "https://e.example/hawa", "highlights": ["Best at sunrise.", "Entry 200 INR."], "image": "https://img"}]})

    async with client_for(handler) as http:
        results = await ExaSearch(http, "exa-key").search("Jaipur sights", 3)
    assert results[0].snippet == "Best at sunrise. Entry 200 INR." and results[0].image == "https://img"


async def test_search_providers_without_keys_refuse_to_start():
    async with httpx.AsyncClient() as http:
        with pytest.raises(RuntimeError):
            TavilySearch(http, "")
        with pytest.raises(RuntimeError):
            ExaSearch(http, "")
    assert await NoWebSearch().search("anything") == []


async def test_openrouter_json_mode():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer or-key"
        body = json.loads(request.content)
        assert body["model"] == "google/gemini-2.5-flash" and body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"hotels": [{"name": "Rambagh Palace", "price_per_night": 42000}]}'}}]})

    async with client_for(handler) as http:
        draft = await OpenRouterLLM(http, "or-key", "google/gemini-2.5-flash", 10).generate_json("p", HotelsDraft)
    assert draft.hotels[0].name == "Rambagh Palace"


def test_airport_resolution():
    assert airports.nearest(12.9716, 77.5946).iata_code == "BLR"  # Bengaluru city centre
    assert airports.nearest(26.9124, 75.7873).iata_code == "JAI"
    assert airports.nearest(0.0, -30.0) is None  # middle of the Atlantic
    assert airports.by_code("del").iata_code == "DEL"
    assert airports.search("jaipur")[0].iata_code == "JAI"


def _fake_flight(price, legs, airline="IndiGo", code="6E"):
    def sd(d, h, m):
        return SimpleNamespace(date=(d.year, d.month, d.day), time=(h, m))

    day = date.today() + timedelta(days=30)
    segs = [
        SimpleNamespace(from_airport=SimpleNamespace(code=a), to_airport=SimpleNamespace(code=b), departure=sd(day, h1, 0), arrival=sd(day, h2, 30), duration=(h2 - h1) * 60 + 30, plane_type="A320neo")
        for a, b, h1, h2 in legs
    ]
    return SimpleNamespace(type=code, price=price, airlines=[airline], flights=segs)


async def test_google_flights_provider(monkeypatch):
    import fast_flights

    calls = {}

    def fake_get_flights(query):
        calls["url"] = query.url()
        return [_fake_flight(12000, [("BLR", "BOM", 6, 8), ("BOM", "JAI", 10, 12)]), _fake_flight(8000, [("BLR", "JAI", 9, 12)]), _fake_flight(0, [])]

    monkeypatch.setattr(fast_flights, "get_flights", fake_get_flights)
    req = FlightSearchRequest(origin="BLR", destination="JAI", departure_date=date.today() + timedelta(days=30), adults=2, currency="INR")
    offers = await GoogleFlightsProvider().search(req)
    assert [o.price.amount for o in offers] == [8000, 12000]  # sorted, empty result dropped
    direct, connecting = offers
    assert direct.bookable is False and direct.provider == "google_flights"
    assert direct.deep_link == calls["url"] and "curr=INR" in direct.deep_link
    assert connecting.slices[0].stops == 1 and connecting.slices[0].duration_minutes == 6 * 60 + 30
    assert (await GoogleFlightsProvider().suggest_airports("goa"))[0].iata_code in {"GOI", "GOX"}


async def test_google_flights_failure_degrades(monkeypatch):
    import fast_flights

    def boom(query):
        raise RuntimeError("Google changed its page")

    monkeypatch.setattr(fast_flights, "get_flights", boom)
    req = FlightSearchRequest(origin="BLR", destination="JAI", departure_date=date.today() + timedelta(days=30))
    assert await GoogleFlightsProvider().search(req) == []
