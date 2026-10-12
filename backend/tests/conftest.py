"""
Test harness: real local MongoDB (database `nomadiq_test`, dropped per session),
all external providers mocked, app driven in-process via httpx ASGITransport.

Requires mongod on MONGODB_URI (default mongodb://127.0.0.1:27017).
"""

import asyncio
import os
import uuid
from datetime import date, timedelta

import httpx
import pytest
from pymongo import AsyncMongoClient

from app.core.cache import Cache
from app.core.config import Settings
from app.core.ratelimit import reset_rate_limits
from app.main import create_app

TEST_DB = "nomadiq_test"
API = "/api/v1"


def make_settings(**overrides) -> Settings:
    base = dict(
        environment="test",
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
        mongodb_db=TEST_DB,
        jwt_secret="test-secret-test-secret-test-secret-123",
        llm_provider="mock",
        flight_provider="mock",
        hotel_provider="mock",
        image_provider="mock",
        video_provider="mock",
        weather_provider="mock",
        knowledge_provider="mock",
        speech_provider="mock",
        rate_limit_auth_per_minute=1000,
        _env_file=None,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(scope="session")
async def app():
    settings = make_settings()
    client = AsyncMongoClient(settings.mongodb_uri)
    await client.drop_database(TEST_DB)
    await client.close()
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app):
    reset_rate_limits()
    Cache.clear_l1()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f"http://test{API}") as c:
        yield c


@pytest.fixture
def db(app):
    from app.core.database import get_db

    return get_db()


@pytest.fixture
def providers(app):
    return app.state.providers


async def register(client: httpx.AsyncClient, name: str = "Test User") -> dict:
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    resp = await client.post("/auth/register", json={"email": email, "password": "secret123", "name": name})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "email": email,
        "password": "secret123",
        "user": body["user"],
        "tokens": body["tokens"],
        "headers": {"Authorization": f"Bearer {body['tokens']['access_token']}"},
    }


@pytest.fixture
async def auth(client):
    return await register(client)


async def wait_for_trip(app, client, headers, trip_id: str, timeout: float = 15) -> dict:
    await app.state.jobs.wait_all(timeout)
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        resp = await client.get(f"/trips/{trip_id}", headers=headers)
        trip = resp.json()
        if trip["status"] in ("ready", "failed") or asyncio.get_running_loop().time() > deadline:
            return trip
        await asyncio.sleep(0.05)


def future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()
