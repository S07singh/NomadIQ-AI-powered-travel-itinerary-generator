"""Thin async repository base over a Mongo collection."""

from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.core.utils import utcnow


class BaseRepository:
    collection_name: str

    def __init__(self, db: AsyncDatabase):
        self.db = db
        self.col = db[self.collection_name]

    async def insert(self, data: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        result = await self.col.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    async def get(self, _id: ObjectId, **filters: Any) -> dict[str, Any] | None:
        return await self.col.find_one({"_id": _id, **filters})

    async def update(self, _id: ObjectId, values: dict[str, Any], **filters: Any) -> dict[str, Any] | None:
        values = {**values, "updated_at": utcnow()}
        return await self.col.find_one_and_update(
            {"_id": _id, **filters}, {"$set": values}, return_document=ReturnDocument.AFTER
        )

    async def delete(self, _id: ObjectId, **filters: Any) -> bool:
        result = await self.col.delete_one({"_id": _id, **filters})
        return result.deleted_count == 1

    async def paginate(
        self,
        query: dict[str, Any],
        page: int,
        limit: int,
        sort: list[tuple[str, int]] | None = None,
        projection: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        cursor = self.col.find(query, projection).sort(sort or [("created_at", -1)]).skip((page - 1) * limit).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await self.col.count_documents(query)
        return items, total
