"""
Two-level cache for low-latency live data:
  L1 — small in-process dict (per worker, microseconds)
  L2 — MongoDB `cache` collection with a TTL index (shared by all workers)

Swap L2 for Redis later without changing callers.
"""

import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

from app.core.utils import stable_hash, utcnow

_L1_MAX = 2048


class Cache:
    _l1: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def __init__(self, db: AsyncDatabase):
        self.col = db["cache"]

    @staticmethod
    def make_key(namespace: str, params: Any) -> str:
        return f"{namespace}:{stable_hash(params)}"

    async def get(self, key: str) -> Any | None:
        hit = self._l1.get(key)
        if hit:
            expires, value = hit
            if expires > time.monotonic():
                self._l1.move_to_end(key)
                return value
            self._l1.pop(key, None)
        doc = await self.col.find_one({"_id": key, "expires_at": {"$gt": utcnow()}})
        if doc is None:
            return None
        remaining = (doc["expires_at"] - utcnow()).total_seconds()
        self._set_l1(key, doc["value"], remaining)
        return doc["value"]

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._set_l1(key, value, ttl_seconds)
        await self.col.update_one(
            {"_id": key},
            {"$set": {"value": value, "expires_at": utcnow() + timedelta(seconds=ttl_seconds)}},
            upsert=True,
        )

    async def get_or_set(self, namespace: str, params: Any, ttl_seconds: int, factory: Callable[[], Awaitable[Any]]) -> Any:
        key = self.make_key(namespace, params)
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        if value is not None:
            await self.set(key, value, ttl_seconds)
        return value

    @classmethod
    def _set_l1(cls, key: str, value: Any, ttl_seconds: float) -> None:
        cls._l1[key] = (time.monotonic() + ttl_seconds, value)
        cls._l1.move_to_end(key)
        while len(cls._l1) > _L1_MAX:
            cls._l1.popitem(last=False)

    @classmethod
    def clear_l1(cls) -> None:
        cls._l1.clear()
