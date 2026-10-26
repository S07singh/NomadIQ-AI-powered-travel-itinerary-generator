"""
Trip generation pipeline (runs in the background job runner).

    web search ─┬► destination_agent ┐
                └► dining_agent      ├─► itinerary_agent ─┐
    hotel_agent ─────────────────────┘   plan_flights ────┴─► enrich (photos/videos/maps/weather) ─► budget ─► save
    geocode destination + origin ─────────────▲

Progress is written to the trip document so clients can poll GET /trips/{id}/status
or stream GET /trips/{id}/events.
"""

import asyncio
import time

from bson import ObjectId
from loguru import logger
from pymongo.asynchronous.database import AsyncDatabase

from app.core.cache import Cache
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.utils import utcnow
from app.modules.planner import agents
from app.modules.planner.budget import compute_budget
from app.modules.planner.enrichment import MediaLookup, enrich_plan
from app.modules.planner.flights import plan_flights
from app.modules.planner.links import hotel_links
from app.modules.planner.research import format_results, gather_research, keep_known_sources
from app.modules.planner.schemas import (
    Attraction,
    DayPlan,
    DiningDraft,
    HotelsDraft,
    HotelSuggestion,
    RestaurantSuggestion,
    TripPlan,
    WebSource,
)
from app.modules.search.service import OfferStore
from app.modules.trips.schemas import TripInputs, TripStatus
from app.providers.registry import Providers

ENRICH_TIMEOUT_SECONDS = 25


class TripPlanner:
    def __init__(self, db: AsyncDatabase, providers: Providers, settings: Settings):
        self.db, self.p, self.settings = db, providers, settings
        self.trips = db["trips"]

    async def _progress(self, trip_id: ObjectId, status: TripStatus, step: str, percent: int, message: str, inc: dict | None = None, **extra) -> None:
        now = utcnow()
        update: dict = {"$set": {"status": status.value, "progress": {"status": status.value, "step": step, "percent": percent, "message": message, "updated_at": now}, "updated_at": now, **extra}}
        if inc:
            update["$inc"] = inc
        await self.trips.update_one({"_id": trip_id}, update)

    async def run(self, trip_id: ObjectId) -> None:
        doc = await self.trips.find_one({"_id": trip_id})
        if doc is None:
            return
        t = TripInputs.model_validate(doc)
        started = time.perf_counter()
        logger.info(f"🧭 Planning trip {trip_id} → {t.destination} ({t.duration_days}d)")
        try:
            await self._progress(trip_id, TripStatus.generating, "research", 10, f"Searching the web for {t.destination}, stays and food…", error=None)
            cache = Cache(self.db)
            lookup = MediaLookup(self.p, cache, self.settings.content_cache_ttl_seconds)
            geocode_task = asyncio.create_task(lookup.geocode(t.destination))
            origin_task = asyncio.create_task(lookup.geocode(t.origin)) if t.origin else None
            # The hotel agent doesn't need web results, so it starts while the search runs.
            hotels_task = asyncio.create_task(agents.hotel_agent(self.p.llm, t))

            research = await gather_research(self.p.search, cache, t)
            dest, dining = await asyncio.gather(
                agents.destination_agent(self.p.llm, t, format_results(research.sights)),
                agents.dining_agent(self.p.llm, t, format_results(research.food)),
                return_exceptions=True,
            )
            (hotels,) = await asyncio.gather(hotels_task, return_exceptions=True)
            if isinstance(dest, BaseException):
                raise dest  # the plan is meaningless without destination research
            if isinstance(hotels, BaseException):
                logger.warning(f"Hotel agent failed, continuing without hotels: {hotels!r}")
                hotels = HotelsDraft()
            if isinstance(dining, BaseException):
                logger.warning(f"Dining agent failed, continuing without restaurants: {dining!r}")
                dining = DiningDraft()
            dropped = keep_known_sources(dest.attractions, research.urls) + keep_known_sources(dining.restaurants, research.urls)
            if dropped:
                logger.info(f"Removed {dropped} source link(s) the model invented")

            await self._progress(trip_id, TripStatus.generating, "itinerary", 50, "Building your day-by-day itinerary and checking flights…")
            location = await self._settle(geocode_task, "destination geocoding")
            origin_place = await self._settle(origin_task, "origin geocoding") if origin_task else None
            flights_coro = plan_flights(self.p.flights, t, origin_place, location) if self.settings.plan_flights else asyncio.sleep(0, None)
            itinerary, flights = await asyncio.gather(agents.itinerary_agent(self.p.llm, t, dest, hotels, dining), flights_coro)

            plan = TripPlan(
                summary=dest.summary,
                highlights=dest.highlights,
                attractions=[Attraction.model_validate(a.model_dump()) for a in dest.attractions],
                hotels=[HotelSuggestion.model_validate(h.model_dump()) for h in hotels.hotels],
                restaurants=[RestaurantSuggestion.model_validate(r.model_dump()) for r in dining.restaurants],
                local_dishes=dining.local_dishes,
                days=[DayPlan.model_validate(d.model_dump()) for d in itinerary.days],
                local_info=dest.local_info,
                packing_list=dest.packing_list,
                travel_tips=dest.travel_tips,
                flights=flights,
                sources=[WebSource(title=r.title, url=r.url) for r in research.sights + research.food],
            )
            self._add_hotel_links(plan, t)
            if flights:
                await OfferStore(self.db, self.settings.offer_ttl_minutes).save_many(flights.outbound + flights.inbound)

            await self._progress(trip_id, TripStatus.generating, "enrich", 75, "Adding photos, videos, maps and weather…")
            try:
                await asyncio.wait_for(enrich_plan(plan, t.destination, t.start_date, t.end_date, lookup, location), ENRICH_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                logger.warning(f"Enrichment timed out for trip {trip_id}; saving plan without some media")

            plan.budget = compute_budget(plan, t)
            plan.generated_at = utcnow()
            plan.generation_ms = int((time.perf_counter() - started) * 1000)
            plan.ai_model = getattr(self.p.llm, "model", None) or self.p.llm.name

            await self._progress(
                trip_id, TripStatus.ready, "done", 100, "Your trip is ready!",
                inc={"plan_version": 1}, plan=plan.model_dump(mode="json"), error=None,
                cover_image=plan.cover_image.model_dump(mode="json") if plan.cover_image else None,
            )
            logger.info(f"✅ Trip {trip_id} planned in {plan.generation_ms} ms ({len(plan.sources)} web sources)")
        except asyncio.CancelledError:
            await self._progress(trip_id, TripStatus.failed, "failed", 0, "Generation was interrupted", error="interrupted")
            raise
        except Exception as exc:
            logger.exception(f"❌ Trip {trip_id} failed: {exc!r}")
            message = exc.message if isinstance(exc, AppError) else "We couldn't generate this trip. Please try again."
            await self._progress(trip_id, TripStatus.failed, "failed", 0, message, error=message)

    @staticmethod
    async def _settle(task: asyncio.Task, what: str, timeout: float = 10):
        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except Exception as exc:
            logger.warning(f"{what} failed: {exc!r}")
            return None

    @staticmethod
    def _add_hotel_links(plan: TripPlan, t: TripInputs) -> None:
        """Booking-site links for every hotel, plus a ready-made POST /search/hotels body for live rates."""
        city = t.destination.split(",")[0].strip()
        rooms = max(1, -(-t.travelers.adults // 2))
        dated = bool(t.start_date and t.end_date and t.end_date > t.start_date)
        hint = (
            {
                "city": city,
                "check_in": t.start_date.isoformat(),
                "check_out": t.end_date.isoformat(),
                "adults": t.travelers.adults,
                "children": t.travelers.children,
                "currency": t.currency,
            }
            if dated
            else None
        )
        for h in plan.hotels:
            h.search_hint = hint
            h.links = hotel_links(h.name, city, t.start_date if dated else None, t.end_date if dated else None, t.travelers.adults, rooms)
