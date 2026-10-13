from datetime import timedelta

from bson import ObjectId

from app.core.utils import utcnow
from tests.conftest import future, register

CONTACT = {"email": "ravi@example.com", "phone": "+919876543210"}
ADULT = {"title": "mr", "given_name": "Ravi", "family_name": "Kumar", "born_on": "1990-05-01", "gender": "m"}


async def first_offer(client, headers, kind="flights", **extra) -> dict:
    bodies = {
        "flights": {"origin": "DEL", "destination": "GOI", "departure_date": future(15), "adults": 1},
        "hotels": {"city": "Goa", "check_in": future(15), "check_out": future(17)},
        "trains": {"origin": "New Delhi", "destination": "Jaipur", "date": future(15)},
    }
    resp = await client.post(f"/search/{kind}", json={**bodies[kind], **extra}, headers=headers)
    return resp.json()["results"][0]


async def quote(client, headers, offer, travelers=None, **extra):
    body = {"offer_id": offer["offer_id"], "travelers": travelers or [ADULT], "contact": CONTACT, **extra}
    return await client.post("/bookings", json=body, headers=headers)


async def test_full_flight_booking_flow(client, auth):
    h = auth["headers"]
    offer = await first_offer(client, h)
    q = await quote(client, h, offer)
    assert q.status_code == 201, q.text
    booking = q.json()
    assert booking["status"] == "awaiting_confirmation"
    assert booking["price"] == offer["price"] and booking["price_changed"] is False
    assert booking["payment"]["status"] == "requires_payment"
    assert booking["provider_reference"] is None

    confirmed = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": booking["price"], "payment_token": "tok_ok"}, headers=h)
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "confirmed"
    assert body["provider_reference"].startswith("MCK") and len(body["tickets"]) == 1
    assert body["payment"]["status"] == "succeeded" and body["confirmed_at"]

    # Confirm is idempotent
    again = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": booking["price"]}, headers=h)
    assert again.json()["provider_reference"] == body["provider_reference"]

    listing = (await client.get("/bookings?status=confirmed", headers=h)).json()
    assert listing["total"] == 1 and listing["items"][0]["title"] == offer["title"]


async def test_idempotency_key_returns_same_booking(client, auth):
    h = {**auth["headers"], "Idempotency-Key": "voice-cmd-123"}
    offer = await first_offer(client, auth["headers"])
    a = (await quote(client, h, offer)).json()
    b = (await quote(client, h, offer)).json()
    assert a["id"] == b["id"]


async def test_price_guard_blocks_mismatch(client, auth):
    h = auth["headers"]
    booking = (await quote(client, h, await first_offer(client, h))).json()
    wrong = {**booking["price"], "amount": booking["price"]["amount"] - 1}
    resp = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": wrong}, headers=h)
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "price_mismatch"
    assert (await client.get(f"/bookings/{booking['id']}", headers=h)).json()["status"] == "awaiting_confirmation"


async def test_payment_declined_then_retry(client, auth):
    h = auth["headers"]
    booking = (await quote(client, h, await first_offer(client, h))).json()
    declined = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": booking["price"], "payment_token": "tok_fail"}, headers=h)
    assert declined.status_code == 402 and declined.json()["error"]["code"] == "payment_failed"
    state = (await client.get(f"/bookings/{booking['id']}", headers=h)).json()
    assert state["status"] == "awaiting_confirmation" and state["failure_reason"]
    ok = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": booking["price"], "payment_token": "tok_ok"}, headers=h)
    assert ok.json()["status"] == "confirmed"


async def test_supplier_failure_refunds(client, auth):
    h = auth["headers"]
    booking = (await quote(client, h, await first_offer(client, h), travelers=[{**ADULT, "family_name": "FAIL"}])).json()
    resp = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": booking["price"]}, headers=h)
    body = resp.json()
    assert body["status"] == "failed"
    assert body["payment"]["status"] == "refunded"
    assert "refunded" in body["failure_reason"]


async def test_expired_hold_cannot_be_confirmed(client, auth, db):
    h = auth["headers"]
    booking = (await quote(client, h, await first_offer(client, h))).json()
    await db["bookings"].update_one({"_id": ObjectId(booking["id"])}, {"$set": {"confirm_before": utcnow() - timedelta(minutes=1)}})
    resp = await client.post(f"/bookings/{booking['id']}/confirm", json={"expected_total": booking["price"]}, headers=h)
    assert resp.status_code == 410
    assert (await client.get(f"/bookings/{booking['id']}", headers=h)).json()["status"] == "expired"


async def test_cancel_flows(client, auth):
    h = auth["headers"]
    held = (await quote(client, h, await first_offer(client, h))).json()
    cancelled = (await client.post(f"/bookings/{held['id']}/cancel", headers=h)).json()
    assert cancelled["status"] == "cancelled"
    assert (await client.post(f"/bookings/{held['id']}/confirm", json={"expected_total": held["price"]}, headers=h)).status_code == 409

    hotel = await first_offer(client, h, "hotels")
    b = (await quote(client, h, hotel)).json()
    await client.post(f"/bookings/{b['id']}/confirm", json={"expected_total": b["price"]}, headers=h)
    c = (await client.post(f"/bookings/{b['id']}/cancel", headers=h)).json()
    assert c["status"] == "cancelled" and c["payment"]["status"] == "refunded" and c["cancelled_at"]
    assert (await client.post(f"/bookings/{b['id']}/cancel", headers=h)).status_code == 409


async def test_traveler_validation(client, auth):
    h = auth["headers"]
    offer = await first_offer(client, h)
    two = await quote(client, h, offer, travelers=[ADULT, ADULT])
    assert two.status_code == 422 and two.json()["error"]["code"] == "traveler_mismatch"
    neither = await client.post("/bookings", json={"offer_id": offer["offer_id"], "contact": CONTACT}, headers=h)
    assert neither.status_code == 422
    both = await client.post("/bookings", json={"offer_id": offer["offer_id"], "contact": CONTACT, "travelers": [ADULT], "traveler_ids": ["x"]}, headers=h)
    assert both.status_code == 422


async def test_saved_traveler_and_trip_link(client, auth):
    h = auth["headers"]
    tid = (await client.post("/users/me/travelers", json={**ADULT, "label": "Me"}, headers=h)).json()["id"]
    trip_id = (await client.post("/trips", json={"destination": "Jaipur", "generate": False}, headers=h)).json()["id"]
    offer = await first_offer(client, h, "trains")
    resp = await client.post("/bookings", json={"offer_id": offer["offer_id"], "traveler_ids": [tid], "contact": CONTACT, "trip_id": trip_id}, headers=h)
    assert resp.status_code == 201
    assert resp.json()["travelers"][0]["given_name"] == "Ravi" and resp.json()["trip_id"] == trip_id
    assert (await client.get(f"/bookings?trip_id={trip_id}", headers=h)).json()["total"] == 1


async def test_booking_isolation_and_expired_offer(client, auth):
    h = auth["headers"]
    booking = (await quote(client, h, await first_offer(client, h))).json()
    other = await register(client)
    assert (await client.get(f"/bookings/{booking['id']}", headers=other["headers"])).status_code == 404
    assert (await client.post(f"/bookings/{booking['id']}/cancel", headers=other["headers"])).status_code == 404
    gone = await client.post("/bookings", json={"offer_id": "mock:fl_missing", "travelers": [ADULT], "contact": CONTACT}, headers=h)
    assert gone.status_code == 410
