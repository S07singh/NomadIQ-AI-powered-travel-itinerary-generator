"""
MongoDB connection (PyMongo Async API — Motor is deprecated).

Works the same with a local mongod (dev/test) and MongoDB Atlas (production):
only MONGODB_URI changes.
"""

from loguru import logger
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel
from pymongo.asynchronous.database import AsyncDatabase


class _Mongo:
    client: AsyncMongoClient | None = None
    db: AsyncDatabase | None = None


mongo = _Mongo()


async def connect_mongo(uri: str, db_name: str) -> AsyncDatabase:
    mongo.client = AsyncMongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000, appname="nomadiq-api")
    mongo.db = mongo.client[db_name]
    await mongo.client.admin.command("ping")
    await ensure_indexes(mongo.db)
    logger.info(f"🍃 Connected to MongoDB database '{db_name}'")
    return mongo.db


async def close_mongo() -> None:
    if mongo.client is not None:
        await mongo.client.close()
    mongo.client = None
    mongo.db = None


def get_db() -> AsyncDatabase:
    if mongo.db is None:
        raise RuntimeError("MongoDB is not connected")
    return mongo.db


INDEXES: dict[str, list[IndexModel]] = {
    "users": [IndexModel([("email", ASCENDING)], unique=True)],
    "refresh_tokens": [
        IndexModel([("jti", ASCENDING)], unique=True),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
    ],
    "travelers": [IndexModel([("user_id", ASCENDING)])],
    "devices": [IndexModel([("token", ASCENDING)], unique=True), IndexModel([("user_id", ASCENDING)])],
    "trips": [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("share_token", ASCENDING)], unique=True, partialFilterExpression={"share_token": {"$type": "string"}}),
        IndexModel([("status", ASCENDING)]),
    ],
    "trip_messages": [IndexModel([("trip_id", ASCENDING), ("created_at", ASCENDING)])],
    "bookings": [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel(
            [("user_id", ASCENDING), ("idempotency_key", ASCENDING)],
            unique=True,
            partialFilterExpression={"idempotency_key": {"$type": "string"}},
        ),
    ],
    "conversations": [IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)])],
    "conversation_messages": [IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)])],
    "cache": [IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0)],
    "offers": [IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0)],
}


async def ensure_indexes(db: AsyncDatabase) -> None:
    for collection, indexes in INDEXES.items():
        await db[collection].create_indexes(indexes)
