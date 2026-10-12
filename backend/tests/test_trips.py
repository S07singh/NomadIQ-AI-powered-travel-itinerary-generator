import json

from tests.conftest import future, register, wait_for_trip

TRIP = {
    "destination": "Goa, India",
    "origin": "Bengaluru",
    "travelers": {"adults": 2, "children": 1},
    "budget": {"amount": 60000, "currency": "INR"},
    "travel_style": "comfort",
    "pace": "moderate",
    "vibes": ["relaxation", "food"],
    "interests": ["beaches", "seafood"],
    "additional_info": "private note: anniversary",
}


async def create_ready_trip(app, client, headers, **overrides) -> dict:
    body = {**TRIP, "start_date": future(3), "end_date": future(5), **overrides}
    resp = await client.post("/trips", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return await wait_for_trip(app, client, headers, resp.json()["id"])


async def test_create_and_generate_full_plan(app, client, auth):
    resp = await client.post("/trips", json={**TRIP, "start_date": future(3), "end_date": future(5)}, headers=auth["headers"])
    created = resp.json()
    assert created["status"] in ("queued", "generating", "ready")
    assert created["duration_days"] == 3
    assert created["title"] == "Trip to Goa"

    trip = await wait_for_trip(app, client, auth["headers"], created["id"])
    assert trip["status"] == "ready", trip.get("error")
    assert trip["progress"]["percent"] == 100
    assert trip["plan_version"] == 1
    plan = trip["plan"]
    assert [d["day"] for d in plan["days"]] == [1, 2, 3]
    assert plan["days"][0]["date"] == future(3)
    assert plan["days"][0]["weather"] is not None  # within forecast horizon
    assert plan["attractions"] and plan["attractions"][0]["images"]
    assert plan["attractions"][0]["maps_url"].startswith("https://www.google.com/maps/search/")
    assert plan["hotels"][0]["search_hint"]["check_in"] == future(3)
    assert plan["cover_image"] and plan["gallery"] and plan["videos"]
    assert plan["days"][0]["items"][0]["image"] is not None  # reused attraction photo
    budget = plan["budget"]
    assert budget["currency"] == "INR"
    assert abs(sum(line["amount"] for line in budget["lines"]) - budget["total"]) < 1
    assert budget["within_budget"] in (True, False)
    assert plan["ai_model"] == "mock" and plan["generation_ms"] >= 0


async def test_create_without_generation_and_defaults(client, auth):
    resp = await client.post("/trips", json={"destination": "Paris", "generate": False}, headers=auth["headers"])
    trip = resp.json()
    assert trip["status"] == "draft" and trip["duration_days"] == 3 and trip["plan"] is None
    assert trip["start_date"] is None


async def test_trip_validation(client, auth):
    h = auth["headers"]
    bad_range = await client.post("/trips", json={"destination": "Goa", "start_date": future(5), "end_date": future(2)}, headers=h)
    assert bad_range.status_code == 422
    too_long = await client.post("/trips", json={"destination": "Goa", "start_date": future(1), "end_date": future(40)}, headers=h)
    assert too_long.status_code == 422
    end_only = await client.post("/trips", json={"destination": "Goa", "end_date": future(2)}, headers=h)
    assert end_only.status_code == 422
    bad_vibe = await client.post("/trips", json={"destination": "Goa", "vibes": ["partying-hard"]}, headers=h)
    assert bad_vibe.status_code == 422


async def test_start_date_plus_duration_derives_end(client, auth):
    resp = await client.post("/trips", json={"destination": "Goa", "start_date": future(10), "duration_days": 4, "generate": False}, headers=auth["headers"])
    assert resp.json()["end_date"] == future(13)


async def test_list_filter_pagination_and_isolation(app, client):
    me, other = await register(client), await register(client)
    for i in range(3):
        await client.post("/trips", json={"destination": f"City {i}", "generate": False}, headers=me["headers"])
    await client.post("/trips", json={"destination": "Elsewhere", "generate": False}, headers=other["headers"])

    page1 = (await client.get("/trips?limit=2&page=1", headers=me["headers"])).json()
    assert page1["total"] == 3 and len(page1["items"]) == 2 and page1["has_more"] is True
    assert page1["items"][0]["destination"] == "City 2"  # newest first
    page2 = (await client.get("/trips?limit=2&page=2", headers=me["headers"])).json()
    assert len(page2["items"]) == 1 and page2["has_more"] is False
    drafts = (await client.get("/trips?status=draft", headers=me["headers"])).json()
    assert drafts["total"] == 3

    trip_id = page1["items"][0]["id"]
    assert (await client.get(f"/trips/{trip_id}", headers=other["headers"])).status_code == 404
    assert (await client.delete(f"/trips/{trip_id}", headers=other["headers"])).status_code == 404


async def test_update_trip_and_regenerate(app, client, auth):
    h = auth["headers"]
    trip = await create_ready_trip(app, client, h)
    upd = await client.patch(f"/trips/{trip['id']}", json={"duration_days": 2, "travel_style": "budget"}, headers=h)
    assert upd.status_code == 200
    body = upd.json()
    assert body["duration_days"] == 2 and body["end_date"] == future(4) and body["travel_style"] == "budget"

    regen = await client.post(f"/trips/{trip['id']}/generate", headers=h)
    assert regen.status_code == 202
    again = await client.post(f"/trips/{trip['id']}/generate", headers=h)
    assert again.status_code in (202, 409)  # 409 if the first run is still in flight
    done = await wait_for_trip(app, client, h, trip["id"])
    assert done["status"] == "ready" and len(done["plan"]["days"]) == 2
    assert done["plan_version"] >= 2


async def test_status_and_sse_events(app, client, auth):
    h = auth["headers"]
    trip = await create_ready_trip(app, client, h)
    status = (await client.get(f"/trips/{trip['id']}/status", headers=h)).json()
    assert status == {**status, "status": "ready", "percent": 100}

    resp = await client.get(f"/trips/{trip['id']}/events", headers=h)
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = [line for line in resp.text.splitlines() if line.startswith("event:")]
    assert events[-1] == "event: done"
    data = json.loads([line for line in resp.text.splitlines() if line.startswith("data:")][-1][5:])
    assert data["status"] == "ready"


async def test_chat_modifies_itinerary(app, client, auth):
    h = auth["headers"]
    trip = await create_ready_trip(app, client, h)

    not_ready = (await client.post("/trips", json={"destination": "Paris", "generate": False}, headers=h)).json()
    assert (await client.post(f"/trips/{not_ready['id']}/chat", json={"message": "add museums"}, headers=h)).status_code == 409

    question = await client.post(f"/trips/{trip['id']}/chat", json={"message": "What should I wear?"}, headers=h)
    assert question.status_code == 200
    assert question.json()["plan_updated"] is False and question.json()["trip"]["plan_version"] == 1

    edit = await client.post(f"/trips/{trip['id']}/chat", json={"message": "Add a night beach party on the last day"}, headers=h)
    body = edit.json()
    assert body["plan_updated"] is True
    assert body["trip"]["plan_version"] == 2
    last_day_titles = [i["title"] for i in body["trip"]["plan"]["days"][-1]["items"]]
    assert any(t.startswith("Added:") for t in last_day_titles)
    assert body["trip"]["plan"]["days"][0]["weather"] is not None  # preserved through edits

    history = (await client.get(f"/trips/{trip['id']}/chat", headers=h)).json()
    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]


async def test_share_and_public_view(app, client, auth):
    h = auth["headers"]
    trip = await create_ready_trip(app, client, h)
    share = (await client.post(f"/trips/{trip['id']}/share", headers=h)).json()
    assert share["share_url"].endswith(share["share_token"])
    again = (await client.post(f"/trips/{trip['id']}/share", headers=h)).json()
    assert again["share_token"] == share["share_token"]  # stable link

    public = await client.get(f"/shared/trips/{share['share_token']}")
    assert public.status_code == 200
    assert public.json()["additional_info"] == ""  # private notes hidden
    assert (await client.get(f"/trips/{trip['id']}", headers=h)).json()["is_shared"] is True

    assert (await client.delete(f"/trips/{trip['id']}/share", headers=h)).status_code == 204
    assert (await client.get(f"/shared/trips/{share['share_token']}")).status_code == 404


async def test_delete_trip(app, client, auth, db):
    h = auth["headers"]
    trip = await create_ready_trip(app, client, h)
    await client.post(f"/trips/{trip['id']}/chat", json={"message": "add museums"}, headers=h)
    assert (await client.delete(f"/trips/{trip['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/trips/{trip['id']}", headers=h)).status_code == 404
    from bson import ObjectId

    assert await db["trip_messages"].count_documents({"trip_id": ObjectId(trip["id"])}) == 0


async def test_failed_generation_reports_error(app, client, auth, providers):
    from app.core.exceptions import ProviderError

    original = providers.llm.generate_json

    async def broken(prompt, schema, **kw):
        raise ProviderError("LLM down", code="llm_unavailable")

    providers.llm.generate_json = broken
    try:
        resp = await client.post("/trips", json={"destination": "Goa"}, headers=auth["headers"])
        trip = await wait_for_trip(app, client, auth["headers"], resp.json()["id"])
    finally:
        providers.llm.generate_json = original
    assert trip["status"] == "failed"
    assert trip["error"] == "LLM down"
    assert trip["progress"]["status"] == "failed"
