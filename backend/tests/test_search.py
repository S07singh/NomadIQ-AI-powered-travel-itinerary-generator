from datetime import timedelta

from app.core.utils import utcnow
from tests.conftest import future

FLIGHT = {"origin": "del", "destination": "BOM", "departure_date": future(20), "adults": 2, "currency": "INR"}


async def test_flight_search_sorted_and_bookable(client, auth):
    resp = await client.post("/search/flights", json=FLIGHT, headers=auth["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kind"] == "flight" and body["provider"] == "mock" and body["cached"] is False
    prices = [o["price"]["amount"] for o in body["results"]]
    assert prices == sorted(prices) and body["count"] == len(prices) > 0
    first = body["results"][0]
    assert first["price"]["currency"] == "INR" and first["passengers"] == 2
    assert first["slices"][0]["origin"] == "DEL"

    offer = await client.get(f"/search/offers/{first['offer_id']}", headers=auth["headers"])
    assert offer.status_code == 200 and offer.json()["offer_id"] == first["offer_id"]

    again = (await client.post("/search/flights", json=FLIGHT, headers=auth["headers"])).json()
    assert again["cached"] is True and again["results"][0]["offer_id"] == first["offer_id"]


async def test_round_trip_and_non_stop(client, auth):
    body = (await client.post("/search/flights", json={**FLIGHT, "return_date": future(25), "non_stop_only": True}, headers=auth["headers"])).json()
    for offer in body["results"]:
        assert len(offer["slices"]) == 2
        assert all(s["stops"] == 0 for s in offer["slices"])


async def test_flight_validation(client, auth):
    h = auth["headers"]
    assert (await client.post("/search/flights", json={**FLIGHT, "departure_date": "2020-01-01"}, headers=h)).status_code == 422
    assert (await client.post("/search/flights", json={**FLIGHT, "destination": "DEL"}, headers=h)).status_code == 422
    assert (await client.post("/search/flights", json={**FLIGHT, "return_date": future(1)}, headers=h)).status_code == 422
    assert (await client.post("/search/flights", json={**FLIGHT, "infants": 3}, headers=h)).status_code == 422
    assert (await client.post("/search/flights", json=FLIGHT)).status_code == 401


async def test_hotel_search_pricing(client, auth):
    req = {"city": "Goa", "check_in": future(10), "check_out": future(13), "adults": 2, "currency": "USD"}
    body = (await client.post("/search/hotels", json=req, headers=auth["headers"])).json()
    assert body["count"] > 0
    h = body["results"][0]
    assert h["nights"] == 3
    assert abs(h["price"]["amount"] - h["price_per_night"]["amount"] * 3) < 0.05
    assert h["images"]
    bad = await client.post("/search/hotels", json={**req, "check_out": req["check_in"]}, headers=auth["headers"])
    assert bad.status_code == 422


async def test_hotel_filters(client, auth):
    req = {"city": "Goa", "check_in": future(10), "check_out": future(12), "min_rating": 4}
    body = (await client.post("/search/hotels", json=req, headers=auth["headers"])).json()
    assert all(h["star_rating"] >= 4 for h in body["results"])


async def test_trains_buses_activities(client, auth):
    h = auth["headers"]
    ground = {"origin": "New Delhi", "destination": "Jaipur", "date": future(7), "passengers": 2, "travel_class": "3A"}
    trains = (await client.post("/search/trains", json=ground, headers=h)).json()
    assert trains["kind"] == "train" and trains["results"][0]["kind"] == "train"
    assert trains["results"][0]["price"]["currency"] == "INR"
    buses = (await client.post("/search/buses", json=ground, headers=h)).json()
    assert buses["kind"] == "bus" and buses["results"][0]["operator"]
    acts = (await client.post("/search/activities", json={"destination": "Goa", "query": "food"}, headers=h)).json()
    assert acts["results"] and "Food" in acts["results"][0]["name"]


async def test_airport_autocomplete(client, auth):
    body = (await client.get("/search/airports?q=goa", headers=auth["headers"])).json()
    assert {a["iata_code"] for a in body} == {"GOI", "GOX"}
    assert (await client.get("/search/airports?q=g", headers=auth["headers"])).status_code == 422


async def test_unknown_and_expired_offers_are_gone(client, auth, db):
    h = auth["headers"]
    assert (await client.get("/search/offers/mock:nope", headers=h)).status_code == 410
    body = (await client.post("/search/flights", json={**FLIGHT, "adults": 1}, headers=h)).json()
    offer_id = body["results"][0]["offer_id"]
    await db["offers"].update_one({"_id": offer_id}, {"$set": {"expires_at": utcnow() - timedelta(seconds=1)}})
    resp = await client.get(f"/search/offers/{offer_id}", headers=h)
    assert resp.status_code == 410 and resp.json()["error"]["code"] == "offer_expired"
