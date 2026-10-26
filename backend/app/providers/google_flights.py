"""
Live Google Flights prices via `fast-flights` (scrapes google.com/travel/flights).

Read-only: offers carry `bookable=False` and a `deep_link` to the same search on Google
Flights, where the user completes the booking. No API key needed, but Google can change
its page at any time, so every failure degrades to "no results + search link".
"""

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.common.schemas import Money
from app.common.travel import (
    BaseOffer,
    ContactInfo,
    FlightOffer,
    FlightSearchRequest,
    FlightSegment,
    FlightSlice,
    ProviderBookingResult,
    TravelerInfo,
)
from app.core.exceptions import AppError
from app.core.utils import stable_hash
from app.providers import airports
from app.providers.base import Airport, FlightProvider

SEAT = {"economy": "economy", "premium_economy": "premium-economy", "business": "business", "first": "first"}
SEARCH_TIMEOUT_SECONDS = 25


def _dt(sd) -> datetime:
    (y, mo, d), (h, mi) = sd.date, sd.time
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def build_query(req: FlightSearchRequest, origin: str, destination: str, date: str):
    from fast_flights import FlightQuery, Passengers, create_query

    return create_query(
        flights=[FlightQuery(date=date, from_airport=origin, to_airport=destination)],
        seat=SEAT[req.cabin_class.value],
        trip="one-way",
        passengers=Passengers(adults=req.adults, children=req.children, infants_on_lap=req.infants),
        language="en-US",
        currency=req.currency,
        max_stops=0 if req.non_stop_only else None,
    )


def to_offer(f, req: FlightSearchRequest, link: str, index: int) -> FlightOffer:
    segs = [
        FlightSegment(
            carrier=(f.airlines[0] if f.airlines else f.type),
            carrier_code=f.type if len(f.type) <= 3 else "",
            flight_number=f.type,  # Google's results page doesn't expose flight numbers
            origin=s.from_airport.code,
            destination=s.to_airport.code,
            departure_at=_dt(s.departure),
            arrival_at=_dt(s.arrival),
            aircraft=s.plane_type or None,
        )
        for s in f.flights
    ]
    total_minutes = int((segs[-1].arrival_at - segs[0].departure_at).total_seconds() // 60) if segs else 0
    slice_ = FlightSlice(
        origin=segs[0].origin,
        destination=segs[-1].destination,
        departure_at=segs[0].departure_at,
        arrival_at=segs[-1].arrival_at,
        duration_minutes=total_minutes,
        stops=max(len(segs) - 1, 0),
        segments=segs,
    )
    airlines = ", ".join(f.airlines) or f.type
    return FlightOffer(
        offer_id=f"google_flights:{stable_hash([req.model_dump(mode='json'), index, f.price])[:16]}",
        provider="google_flights",
        title=f"{airlines} {slice_.origin}→{slice_.destination}",
        price=Money(amount=float(f.price), currency=req.currency),
        bookable=False,
        deep_link=link,
        slices=[slice_],
        cabin_class=req.cabin_class,
        passengers=req.adults + req.children + req.infants,
    )


class GoogleFlightsProvider(FlightProvider):
    name = "google_flights"

    async def _one_way(self, req: FlightSearchRequest, origin: str, destination: str, date: str) -> tuple[list, str]:
        query = build_query(req, origin, destination, date)
        link = query.url()

        def fetch():
            from fast_flights import get_flights

            return list(get_flights(query))

        try:
            results = await asyncio.wait_for(asyncio.to_thread(fetch), SEARCH_TIMEOUT_SECONDS)
        except Exception as exc:  # scraper errors, timeouts, "no flights" exceptions
            logger.warning(f"Google Flights search failed {origin}->{destination} {date}: {exc!r}")
            results = []
        return results, link

    async def search(self, req: FlightSearchRequest) -> list[FlightOffer]:
        flights, link = await self._one_way(req, req.origin, req.destination, req.departure_date.isoformat())
        offers = [to_offer(f, req, link, i) for i, f in enumerate(flights) if f.flights and f.price]
        if req.non_stop_only:
            offers = [o for o in offers if o.slices[0].stops == 0]
        offers.sort(key=lambda o: o.price.amount)
        return offers[: req.max_results]

    async def suggest_airports(self, query: str, limit: int = 8) -> list[Airport]:
        return airports.search(query, limit)

    async def book(self, offer: BaseOffer, travelers: list[TravelerInfo], contact: ContactInfo) -> ProviderBookingResult:
        raise AppError("This fare is booked on Google Flights", code="external_booking", status_code=409, details={"deep_link": offer.deep_link})
