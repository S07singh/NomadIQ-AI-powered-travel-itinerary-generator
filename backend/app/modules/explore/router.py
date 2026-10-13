"""
Explore: visual + live destination data for discovery screens (no login needed).
All lookups are cached and run in parallel for low latency.
"""

import asyncio
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.common.schemas import APIModel, MediaImage, Place, VideoLink, WeatherDay
from app.core.cache import Cache
from app.core.deps import DB, ProvidersDep, SettingsDep
from app.core.exceptions import AppError
from app.core.ratelimit import rate_limit
from app.modules.planner.enrichment import MediaLookup
from app.providers.media import PlaceSummary, maps_url
from app.providers.weather import FORECAST_HORIZON_DAYS

router = APIRouter(prefix="/explore", tags=["Explore"], dependencies=[Depends(rate_limit("explore", per_minute=120))])

Q = Annotated[str, Query(min_length=2, max_length=100)]


class DestinationOverview(APIModel):
    query: str
    place: Place | None = None
    summary: PlaceSummary | None = None
    images: list[MediaImage] = []
    videos: list[VideoLink] = []
    weather: list[WeatherDay] = []
    maps_url: str


def get_lookup(db: DB, providers: ProvidersDep, settings: SettingsDep) -> MediaLookup:
    return MediaLookup(providers, Cache(db), settings.content_cache_ttl_seconds)


Lookup = Annotated[MediaLookup, Depends(get_lookup)]


@router.get("/places", response_model=list[Place], summary="Destination autocomplete (geocoding)")
async def places(q: Q, providers: ProvidersDep, db: DB, limit: Annotated[int, Query(ge=1, le=10)] = 5):
    async def fetch():
        return [p.model_dump(mode="json") for p in await providers.weather.geocode(q, limit)]

    data = await Cache(db).get_or_set("places", [q.lower(), limit], 24 * 3600, fetch)
    return [Place.model_validate(p) for p in data or []]


@router.get("/destination", response_model=DestinationOverview, summary="Photos, videos, summary, weather and map for a destination")
async def destination(q: Q, lookup: Lookup, providers: ProvidersDep, db: DB, settings: SettingsDep):
    async def build():
        city = q.split(",")[0].strip()
        place, summary, images, videos = await asyncio.gather(
            lookup.geocode(q),
            providers.knowledge.summary(city),
            lookup.images(f"{q} tourism", 8),
            lookup.videos(f"{city} travel guide", 3),
        )
        weather = await lookup.forecast(place, date.today(), date.today() + timedelta(days=6)) if place else []
        return DestinationOverview(
            query=q, place=place, summary=summary, images=images, videos=videos, weather=weather, maps_url=maps_url(q)
        ).model_dump(mode="json")

    data = await Cache(db).get_or_set("overview", [q.lower(), providers.images.name], 3 * 3600, build)
    return DestinationOverview.model_validate(data)


@router.get("/images", response_model=list[MediaImage], summary="Search place/food/hotel photos")
async def images(q: Q, lookup: Lookup, limit: Annotated[int, Query(ge=1, le=20)] = 6):
    return await lookup.images(q, limit)


@router.get("/videos", response_model=list[VideoLink], summary="Search travel videos")
async def videos(q: Q, lookup: Lookup, limit: Annotated[int, Query(ge=1, le=10)] = 3):
    return await lookup.videos(q, limit)


@router.get("/weather", response_model=list[WeatherDay], summary=f"Daily forecast (up to {FORECAST_HORIZON_DAYS} days ahead)")
async def weather(
    lookup: Lookup,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    start: date | None = None,
    end: date | None = None,
):
    start = start or date.today()
    end = end or start + timedelta(days=6)
    if end < start:
        raise AppError("end must be on or after start", code="invalid_range", status_code=422)
    return await lookup.forecast(Place(name="point", lat=lat, lng=lng), start, end)
