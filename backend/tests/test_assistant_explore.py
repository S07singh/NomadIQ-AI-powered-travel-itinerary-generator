from app.modules.assistant.schemas import AssistantDecision, AssistantIntent
from app.providers.llm import MockLLM
from tests.conftest import wait_for_trip

TRAVELER = {"label": "Me", "title": "ms", "given_name": "Asha", "family_name": "Rao", "born_on": "1992-02-02", "gender": "f", "phone": "+919000000000"}


async def say(client, headers, message, **extra):
    resp = await client.post("/assistant/messages", json={"message": message, **extra}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_small_talk_and_conversation_history(client, auth):
    h = auth["headers"]
    first = await say(client, h, "hello there")
    assert first["message"]["intent"] == "chat" and first["message"]["content"]
    conv = first["conversation_id"]
    await say(client, h, "and what else can you do?", conversation_id=conv)

    convs = (await client.get("/assistant/conversations", headers=h)).json()
    assert convs["total"] == 1 and convs["items"][0]["title"] == "hello there"
    msgs = (await client.get(f"/assistant/conversations/{conv}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]

    assert (await client.delete(f"/assistant/conversations/{conv}", headers=h)).status_code == 204
    assert (await client.get(f"/assistant/conversations/{conv}/messages", headers=h)).status_code == 404


async def test_search_intents_return_offers(client, auth):
    h = auth["headers"]
    for message, kind in [("find me a flight to mumbai", "flight"), ("any hotel in goa?", "hotel"), ("train to jaipur", "train"), ("bus to goa", "bus"), ("food tours", "activity")]:
        body = await say(client, h, message)
        action = body["message"]["actions"][0]
        assert action["type"] == "show_offers" and action["data"]["kind"] == kind
        assert 0 < len(action["data"]["results"]) <= 5
        assert "Cheapest" in body["message"]["content"]


async def test_plan_trip_intent_creates_trip(app, client, auth):
    h = auth["headers"]
    body = await say(client, h, "plan a trip to jaipur for 2 days")
    action = body["message"]["actions"][0]
    assert action["type"] == "trip_created" and action["data"]["destination"] == "Jaipur"
    trip = await wait_for_trip(app, client, h, action["data"]["trip_id"])
    assert trip["status"] == "ready" and trip["duration_days"] == 2


async def test_voice_booking_only_quotes_never_confirms(client, auth):
    h = auth["headers"]
    search = await say(client, h, "find me a flight")
    offer_id = search["message"]["actions"][0]["data"]["results"][0]["offer_id"]

    no_traveler = await say(client, h, "book this", selected_offer_id=offer_id)
    assert no_traveler["message"]["actions"][0]["data"]["missing"] == ["saved_traveler"]

    await client.post("/users/me/travelers", json=TRAVELER, headers=h)
    held = await say(client, h, "book this", selected_offer_id=offer_id)
    action = held["message"]["actions"][0]
    assert action["type"] == "booking_quote" and action["data"]["requires_confirmation"] is True
    booking = (await client.get(f"/bookings/{action['data']['booking_id']}", headers=h)).json()
    assert booking["status"] == "awaiting_confirmation"  # user must still confirm in the UI


async def test_book_without_selection_asks(client, auth):
    body = await say(client, auth["headers"], "book it")
    assert body["message"]["actions"][0]["data"]["missing"] == ["offer_id"]


async def test_modify_trip_intent(app, client, auth):
    h = auth["headers"]
    trip_id = (await client.post("/trips", json={"destination": "Goa"}, headers=h)).json()["id"]
    await wait_for_trip(app, client, h, trip_id)
    body = await say(client, h, "add a spa afternoon", trip_id=trip_id)
    action = body["message"]["actions"][0]
    assert action["type"] == "trip_updated" and action["data"]["plan_version"] == 2


async def test_missing_params_become_needs_info(client, auth, providers):
    class MissingDate(MockLLM):
        async def generate_json(self, prompt, schema, system="", temperature=0.3, retries=1):
            return AssistantDecision(intent=AssistantIntent.search_flights, reply="", params={"origin": "DEL", "destination": "BOM"})

    original = providers.llm
    providers.llm = MissingDate()
    try:
        body = await say(client, auth["headers"], "flight to mumbai")
    finally:
        providers.llm = original
    action = body["message"]["actions"][0]
    assert action["type"] == "needs_info" and "departure_date" in action["data"]["missing"]
    assert "departure date" in body["message"]["content"]


async def test_voice_transcribe_and_assistant(client, auth):
    h = auth["headers"]
    t = await client.post("/voice/transcribe", files={"audio": ("a.webm", b"find me a hotel in goa", "audio/webm")}, headers=h)
    assert t.status_code == 200 and t.json()["text"] == "find me a hotel in goa"

    v = await client.post("/voice/assistant", files={"audio": ("a.m4a", b"find me a hotel in goa", "audio/mp4")}, headers=h)
    body = v.json()
    assert body["transcript"] == "find me a hotel in goa"
    assert body["message"]["actions"][0]["data"]["kind"] == "hotel"


async def test_voice_rejects_bad_uploads(app, client, auth):
    h = auth["headers"]
    wrong = await client.post("/voice/transcribe", files={"audio": ("a.txt", b"hi", "text/plain")}, headers=h)
    assert wrong.status_code == 415
    empty = await client.post("/voice/transcribe", files={"audio": ("a.wav", b"", "audio/wav")}, headers=h)
    assert empty.status_code == 422
    limit = app.state.settings.max_audio_bytes
    app.state.settings.max_audio_bytes = 10
    try:
        big = await client.post("/voice/transcribe", files={"audio": ("a.wav", b"x" * 11, "audio/wav")}, headers=h)
    finally:
        app.state.settings.max_audio_bytes = limit
    assert big.status_code == 413


async def test_explore_endpoints(client):
    places = (await client.get("/explore/places?q=goa")).json()
    assert places[0]["country_code"] == "IN"

    overview = await client.get("/explore/destination?q=Goa, India")
    body = overview.json()
    assert overview.status_code == 200
    assert body["place"]["name"] == "Goa" and body["summary"]["summary"]
    assert len(body["images"]) == 8 and body["videos"] and body["weather"]
    assert body["maps_url"].startswith("https://www.google.com/maps/search/")

    assert len((await client.get("/explore/images?q=taj mahal&limit=3")).json()) == 3
    assert (await client.get("/explore/videos?q=goa beaches")).json()[0]["url"].startswith("https://www.youtube.com/")
    wx = await client.get("/explore/weather?lat=15.3&lng=74.1")
    assert wx.status_code == 200 and len(wx.json()) == 7
    assert (await client.get("/explore/weather?lat=15.3&lng=74.1&start=2030-01-05&end=2030-01-01")).status_code == 422
    assert (await client.get("/explore/weather?lat=95&lng=74.1")).status_code == 422
