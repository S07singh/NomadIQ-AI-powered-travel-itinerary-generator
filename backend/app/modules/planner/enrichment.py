"""
Enrich a plan with visuals and live data: photos, videos, maps links, weather.

Everything runs concurrently with a semaphore, results are cached (Mongo TTL +
in-process), and every lookup is best-effort — a slow or failing provider never
fails trip generation.
"""

import asyncio
from datetime import date, timedelta

from loguru import logger

from app.common.schemas import MediaImage, Place, VideoLink, WeatherDay
from app.core.cache import Cache
from app.modules.planner.schemas import TripPlan
from app.providers.media import maps_url
from app.providers.registry import Providers

MAX_CONCURRENCY = 8


class MediaLookup:
    """Cached, concurrency-limited access to media + weather providers."""

    def __init__(self, providers: Providers, cache: Cache, ttl: int):
        self.p, self.cache, self.ttl = providers, cache, ttl
        self.sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def images(self, query: str, limit: int) -> list[MediaImage]:
        async def fetch():
            async with self.sem:
                return [i.model_dump(mode="json") for i in await self.p.images.search(query, limit)]

        data = await self.cache.get_or_set("img", [self.p.images.name, query, limit], self.ttl, fetch)
        return [MediaImage.model_validate(i) for i in data or []]

    async def videos(self, query: str, limit: int) -> list[VideoLink]:
        async def fetch():
            async with self.sem:
                return [v.model_dump(mode="json") for v in await self.p.videos.search(query, limit)]

        data = await self.cache.get_or_set("vid", [self.p.videos.name, query, limit], self.ttl, fetch)
        return [VideoLink.model_validate(v) for v in data or []]

    async def geocode(self, query: str) -> Place | None:
        async def fetch():
            async with self.sem:
                return [p.model_dump(mode="json") for p in await self.p.weather.geocode(query, 1)]

        data = await self.cache.get_or_set("geo", [query.lower()], self.ttl * 4, fetch)
        return Place.model_validate(data[0]) if data else None

    async def forecast(self, place: Place, start: date, end: date) -> list[WeatherDay]:
        async def fetch():
            async with self.sem:
                return [w.model_dump(mode="json") for w in await self.p.weather.forecast(place.lat, place.lng, start, end)]

        data = await self.cache.get_or_set("wx", [round(place.lat, 2), round(place.lng, 2), str(start), str(end)], 3 * 3600, fetch)
        return [WeatherDay.model_validate(w) for w in data or []]


async def _safe(coro, default):
    try:
        return await coro
    except Exception as exc:  # enrichment must never break planning
        logger.warning(f"Enrichment step failed: {exc!r}")
        return default


def add_maps_links(plan: TripPlan, destination: str) -> None:
    """Pure/no-network: maps deep links for every place + item."""
    for a in plan.attractions:
        a.maps_url = maps_url(a.name, a.area, destination)
    for h in plan.hotels:
        h.maps_url = maps_url(h.name, h.area, destination)
    for r in plan.restaurants:
        r.maps_url = maps_url(r.name, r.area, destination)
    for day in plan.days:
        for item in day.items:
            if item.place_name:
                item.maps_url = maps_url(item.place_name, destination)


def assign_dates(plan: TripPlan, start: date | None) -> None:
    if not start:
        return
    for day in plan.days:
        day.date = start + timedelta(days=day.day - 1)


async def enrich_plan(plan: TripPlan, destination: str, start: date | None, end: date | None, lookup: MediaLookup, location: Place | None) -> None:
    add_maps_links(plan, destination)
    assign_dates(plan, start)
    plan.location = location

    city = destination.split(",")[0].strip()
    gallery_t = _safe(lookup.images(f"{destination} tourism", 6), [])
    videos_t = _safe(asyncio.gather(lookup.videos(f"{city} travel guide", 2), lookup.videos(f"{city} street food", 1)), [[], []])
    attraction_t = [_safe(lookup.images(f"{a.name} {city}", 2), []) for a in plan.attractions]
    attraction_video_t = [_safe(lookup.videos(f"{a.name} {city}", 1), []) for a in plan.attractions[:6]]
    weather_t = _safe(lookup.forecast(location, start, end), []) if (location and start and end) else asyncio.sleep(0, [])

    gallery, video_groups, weather, attr_images, attr_videos = await asyncio.gather(
        gallery_t, videos_t, weather_t, asyncio.gather(*attraction_t), asyncio.gather(*attraction_video_t)
    )

    plan.gallery = gallery
    plan.videos = [v for group in video_groups for v in group]
    for a, imgs in zip(plan.attractions, attr_images):
        a.images = imgs
    for a, vids in zip(plan.attractions, attr_videos):
        a.videos = vids
    plan.cover_image = (gallery or [None])[0] or next((a.images[0] for a in plan.attractions if a.images), None)

    # Reuse attraction photos on itinerary items that visit them.
    by_name = {a.name.lower(): a for a in plan.attractions}
    for day in plan.days:
        for item in day.items:
            match = by_name.get(item.place_name.lower())
            if match and match.images:
                item.image = match.images[0]

    plan.weather = weather
    by_date = {w.date: w for w in weather}
    for day in plan.days:
        if day.date in by_date:
            day.weather = by_date[day.date]
