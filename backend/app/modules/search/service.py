"""
Live inventory search across providers, with:
  - short result caching (identical searches within SEARCH_CACHE_TTL are instant)
  - an offer store (Mongo, TTL-indexed) so any offer_id can be booked later
    without trusting price data sent back by the client.
"""

from collections.abc import Awaitable, Callable
from datetime import timedelta

from pymongo import UpdateOne
from pymongo.asynchronous.database import AsyncDatabase

from app.common.travel import (
    ActivityOffer,
    ActivitySearchRequest,
    AnyOffer,
    BaseOffer,
    FlightOffer,
    FlightSearchRequest,
    GroundSearchRequest,
    HotelOffer,
    HotelSearchRequest,
    OfferKind,
    TransportOffer,
    parse_offer,
)
from app.core.cache import Cache
from app.core.config import Settings
from app.core.exceptions import GoneError
from app.core.utils import utcnow
from app.modules.search.schemas import SearchResponse
from app.providers.base import Airport
from app.providers.registry import Providers


class OfferStore:
    def __init__(self, db: AsyncDatabase, ttl_minutes: int):
        self.col = db["offers"]
        self.ttl = timedelta(minutes=ttl_minutes)

    async def save_many(self, offers: list[BaseOffer]) -> None:
        if not offers:
            return
        now = utcnow()
        ops = []
        for o in offers:
            expires = min(o.expires_at, now + self.ttl) if o.expires_at else now + self.ttl
            ops.append(UpdateOne({"_id": o.offer_id}, {"$set": {"data": o.model_dump(mode="json"), "kind": o.kind.value, "provider": o.provider, "expires_at": expires}}, upsert=True))
        await self.col.bulk_write(ops, ordered=False)

    async def get(self, offer_id: str) -> AnyOffer:
        doc = await self.col.find_one({"_id": offer_id, "expires_at": {"$gt": utcnow()}})
        if doc is None:
            raise GoneError("This offer has expired. Please search again for current prices.", code="offer_expired")
        return parse_offer(doc["data"])


class SearchService:
    def __init__(self, db: AsyncDatabase, providers: Providers, settings: Settings):
        self.p, self.settings = providers, settings
        self.cache = Cache(db)
        self.offers = OfferStore(db, settings.offer_ttl_minutes)

    async def _search(self, kind: OfferKind, provider_name: str, params: dict, model: type[BaseOffer], run: Callable[[], Awaitable[list]]) -> SearchResponse:
        key = Cache.make_key(f"search:{kind.value}", [provider_name, params])
        cached = await self.cache.get(key)
        if cached is not None:
            results = [model.model_validate(o) for o in cached]
            # Cached results must still be bookable: refresh their offer-store entries.
            await self.offers.save_many(results)
            return SearchResponse(kind=kind, provider=provider_name, count=len(results), results=results, cached=True, searched_at=utcnow())
        results = await run()
        await self.offers.save_many(results)
        await self.cache.set(key, [r.model_dump(mode="json") for r in results], self.settings.search_cache_ttl_seconds)
        return SearchResponse(kind=kind, provider=provider_name, count=len(results), results=results, searched_at=utcnow())

    async def flights(self, req: FlightSearchRequest) -> SearchResponse[FlightOffer]:
        return await self._search(OfferKind.flight, self.p.flights.name, req.model_dump(mode="json"), FlightOffer, lambda: self.p.flights.search(req))

    async def hotels(self, req: HotelSearchRequest) -> SearchResponse[HotelOffer]:
        return await self._search(OfferKind.hotel, self.p.hotels.name, req.model_dump(mode="json"), HotelOffer, lambda: self.p.hotels.search(req))

    async def ground(self, mode: OfferKind, req: GroundSearchRequest) -> SearchResponse[TransportOffer]:
        return await self._search(mode, self.p.ground.name, req.model_dump(mode="json"), TransportOffer, lambda: self.p.ground.search(mode, req))

    async def activities(self, req: ActivitySearchRequest) -> SearchResponse[ActivityOffer]:
        return await self._search(OfferKind.activity, self.p.activities.name, req.model_dump(mode="json"), ActivityOffer, lambda: self.p.activities.search(req))

    async def airports(self, query: str) -> list[Airport]:
        async def fetch():
            return [a.model_dump() for a in await self.p.flights.suggest_airports(query)]

        data = await self.cache.get_or_set("airports", [self.p.flights.name, query.lower()], 24 * 3600, fetch)
        return [Airport.model_validate(a) for a in data or []]

    async def get_offer(self, offer_id: str) -> AnyOffer:
        return await self.offers.get(offer_id)
