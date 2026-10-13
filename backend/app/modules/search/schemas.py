from datetime import datetime
from typing import Generic, TypeVar

from app.common.schemas import APIModel
from app.common.travel import OfferKind

T = TypeVar("T")


class SearchResponse(APIModel, Generic[T]):
    kind: OfferKind
    provider: str
    count: int
    results: list[T]
    cached: bool = False
    searched_at: datetime
