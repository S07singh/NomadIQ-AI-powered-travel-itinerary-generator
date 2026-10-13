from app.core.ratelimit import reset_rate_limits
from tests.conftest import register


async def test_health_and_ready(client):
    assert (await client.get("/health")).json()["status"] == "ok"
    ready = await client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["mongo"] == "ok"


async def test_meta_config(client):
    body = (await client.get("/meta/config")).json()
    assert "comfort" in body["enums"]["travel_styles"]
    assert "train" in body["enums"]["offer_kinds"]
    assert body["features"]["live_flights"] is False
    assert body["providers"]["llm"] == "mock"


async def test_openapi_schema_builds(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/bookings/{booking_id}/confirm" in paths
    assert "/api/v1/voice/assistant" in paths


async def test_register_login_me(client):
    auth = await register(client, name="Asha")
    assert auth["user"]["name"] == "Asha"
    assert auth["user"]["preferences"]["currency"] == "USD"
    assert "password_hash" not in auth["user"]

    login = await client.post("/auth/login", json={"email": auth["email"].upper(), "password": "secret123"})
    assert login.status_code == 200
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {login.json()['tokens']['access_token']}"})
    assert me.json()["email"] == auth["email"]


async def test_register_validation_and_duplicates(client):
    auth = await register(client)
    dup = await client.post("/auth/register", json={"email": auth["email"], "password": "secret123", "name": "X"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "email_taken"
    weak = await client.post("/auth/register", json={"email": "weak@example.com", "password": "abcdefgh", "name": "X"})
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "validation_error"
    bad_email = await client.post("/auth/register", json={"email": "nope", "password": "secret123", "name": "X"})
    assert bad_email.status_code == 422


async def test_login_wrong_password(client, auth):
    resp = await client.post("/auth/login", json={"email": auth["email"], "password": "wrong-pass1"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


async def test_protected_route_requires_token(client):
    assert (await client.get("/users/me")).status_code == 401
    bad = await client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "invalid_token"


async def test_refresh_rotation_and_reuse_detection(client, auth):
    old_refresh = auth["tokens"]["refresh_token"]
    rotated = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Re-using the old token = theft signal -> whole family revoked
    reuse = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401 and reuse.json()["error"]["code"] == "token_revoked"
    assert (await client.post("/auth/refresh", json={"refresh_token": new_refresh})).status_code == 401


async def test_access_token_cannot_refresh(client, auth):
    resp = await client.post("/auth/refresh", json={"refresh_token": auth["tokens"]["access_token"]})
    assert resp.status_code == 401


async def test_logout_revokes_refresh(client, auth):
    assert (await client.post("/auth/logout", json={"refresh_token": auth["tokens"]["refresh_token"]})).status_code == 204
    assert (await client.post("/auth/refresh", json={"refresh_token": auth["tokens"]["refresh_token"]})).status_code == 401


async def test_change_password(client, auth):
    h = auth["headers"]
    wrong = await client.post("/auth/password/change", json={"current_password": "nope", "new_password": "newpass123"}, headers=h)
    assert wrong.status_code == 401
    ok = await client.post("/auth/password/change", json={"current_password": "secret123", "new_password": "newpass123"}, headers=h)
    assert ok.status_code == 204
    assert (await client.post("/auth/login", json={"email": auth["email"], "password": "newpass123"})).status_code == 200
    assert (await client.post("/auth/refresh", json={"refresh_token": auth["tokens"]["refresh_token"]})).status_code == 401


async def test_auth_rate_limit(app, client):
    settings = app.state.settings
    original = settings.rate_limit_auth_per_minute
    settings.rate_limit_auth_per_minute = 3
    reset_rate_limits()
    try:
        codes = [(await client.post("/auth/login", json={"email": "a@example.com", "password": "x"})).status_code for _ in range(4)]
    finally:
        settings.rate_limit_auth_per_minute = original
        reset_rate_limits()
    assert codes[:3] == [401, 401, 401]
    assert codes[3] == 429
