from tests.conftest import register

TRAVELER = {"label": "Me", "title": "mr", "given_name": "Ravi", "family_name": "Kumar", "born_on": "1990-05-01", "gender": "m", "email": "ravi@example.com", "phone": "+919876543210"}


async def test_update_profile_merges_preferences(client, auth):
    h = auth["headers"]
    r1 = await client.patch("/users/me", json={"name": "Ravi", "preferences": {"currency": "INR", "home_airport": "BLR"}}, headers=h)
    assert r1.status_code == 200
    r2 = await client.patch("/users/me", json={"preferences": {"travel_style": "budget"}}, headers=h)
    prefs = r2.json()["preferences"]
    assert r2.json()["name"] == "Ravi"
    assert prefs["currency"] == "INR" and prefs["home_airport"] == "BLR" and prefs["travel_style"] == "budget"


async def test_invalid_preference_rejected(client, auth):
    resp = await client.patch("/users/me", json={"preferences": {"travel_style": "yacht"}}, headers=auth["headers"])
    assert resp.status_code == 422


async def test_travelers_crud_and_isolation(client, auth):
    h = auth["headers"]
    created = await client.post("/users/me/travelers", json=TRAVELER, headers=h)
    assert created.status_code == 201
    tid = created.json()["id"]

    upd = await client.patch(f"/users/me/travelers/{tid}", json={"phone": "+911111111111"}, headers=h)
    assert upd.json()["phone"] == "+911111111111" and upd.json()["given_name"] == "Ravi"
    assert len((await client.get("/users/me/travelers", headers=h)).json()) == 1

    other = await register(client)
    assert (await client.patch(f"/users/me/travelers/{tid}", json={"phone": "+922"}, headers=other["headers"])).status_code == 404
    assert (await client.delete(f"/users/me/travelers/{tid}", headers=other["headers"])).status_code == 404
    assert (await client.delete("/users/me/travelers/not-an-id", headers=h)).status_code == 404

    assert (await client.delete(f"/users/me/travelers/{tid}", headers=h)).status_code == 204
    assert (await client.get("/users/me/travelers", headers=h)).json() == []


async def test_devices_upsert(client, auth):
    h = auth["headers"]
    body = {"token": "ExponentPushToken[abcdef123456]", "platform": "android", "app_version": "1.0.0"}
    first = await client.post("/users/me/devices", json=body, headers=h)
    second = await client.post("/users/me/devices", json={**body, "app_version": "1.1.0"}, headers=h)
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["app_version"] == "1.1.0"
    assert (await client.delete(f"/users/me/devices/{body['token']}", headers=h)).status_code == 204


async def test_delete_account_cascades(client, db):
    auth = await register(client)
    h = auth["headers"]
    await client.post("/users/me/travelers", json=TRAVELER, headers=h)
    await client.post("/trips", json={"destination": "Goa", "generate": False}, headers=h)
    assert (await client.delete("/users/me", headers=h)).status_code == 204
    assert (await client.get("/users/me", headers=h)).status_code == 401
    assert await db["users"].count_documents({"email": auth["email"]}) == 0
    from bson import ObjectId

    uid = ObjectId(auth["user"]["id"])
    assert await db["trips"].count_documents({"user_id": uid}) == 0
    assert await db["travelers"].count_documents({"user_id": uid}) == 0
