"""Small shared helpers."""

import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.core.exceptions import NotFoundError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_object_id(value: str, what: str = "Resource") -> ObjectId:
    """Parse a path id; an invalid id is reported as 404 (not 500/422) so ids stay opaque."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise NotFoundError(f"{what} not found")


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Mongo document -> API dict: `_id` becomes string `id`, ObjectId refs become strings."""
    if doc is None:
        return None
    out = {}
    for key, value in doc.items():
        if key == "_id":
            out["id"] = str(value)
        elif isinstance(value, ObjectId):
            out[key] = str(value)
        else:
            out[key] = value
    return out


def stable_hash(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def new_token(nbytes: int = 24) -> str:
    return secrets.token_urlsafe(nbytes)
