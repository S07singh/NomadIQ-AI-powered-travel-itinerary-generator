"""
Flight options for a plan: resolve both cities to airports (offline dataset), search the
configured flight provider for the outbound and return days in parallel, and always attach
Google Flights / Kayak links so the user can book even when live search finds nothing.
"""

import asyncio
from datetime import date

from loguru import logger

from app.common.schemas import Place
from app.common.travel import FlightOffer, FlightSearchRequest
from app.modules.planner.links import flight_links
from app.modules.planner.schemas import PlanFlights
from app.modules.trips.schemas import TripInputs
from app.providers import airports
from app.providers.base import FlightProvider

OPTIONS_PER_DIRECTION = 4


async def _search(provider: FlightProvider, req: FlightSearchRequest) -> list[FlightOffer]:
    try:
        return (await provider.search(req))[:OPTIONS_PER_DIRECTION]
    except Exception as exc:
        logger.warning(f"Plan flight search failed {req.origin}->{req.destination}: {exc!r}")
        return []


async def plan_flights(provider: FlightProvider, t: TripInputs, origin: Place | None, destination: Place | None) -> PlanFlights | None:
    if not t.origin or not t.start_date:
        return None  # nothing to search without a starting city and a first day
    if t.start_date < date.today():
        return None
    from_airport = airports.nearest(origin.lat, origin.lng) if origin else None
    to_airport = airports.nearest(destination.lat, destination.lng) if destination else None
    if not from_airport or not to_airport:
        return PlanFlights(note=f"We couldn't find an airport near {t.origin if not from_airport else t.destination}. Trains or buses may suit this route.")
    if from_airport.iata_code == to_airport.iata_code:
        return PlanFlights(origin_airport=from_airport, destination_airport=to_airport, note="Both cities use the same airport, so there's no flight to book.")

    back = t.end_date if t.end_date and t.end_date > t.start_date else None
    base = {
        "adults": min(t.travelers.adults, 9),
        "children": min(t.travelers.children, 8),
        "infants": min(t.travelers.infants, t.travelers.adults, 4),
        "currency": t.currency,
        "max_results": OPTIONS_PER_DIRECTION * 2,
    }
    out_req = FlightSearchRequest(origin=from_airport.iata_code, destination=to_airport.iata_code, departure_date=t.start_date, **base)
    tasks = [_search(provider, out_req)]
    if back:
        tasks.append(_search(provider, FlightSearchRequest(origin=to_airport.iata_code, destination=from_airport.iata_code, departure_date=back, **base)))
    results = await asyncio.gather(*tasks)

    outbound = results[0]
    inbound = results[1] if back else []
    note = "" if outbound else "Live prices aren't available for this route right now. Use the links to compare fares."
    return PlanFlights(
        origin_airport=from_airport,
        destination_airport=to_airport,
        outbound=outbound,
        inbound=inbound,
        links=flight_links(from_airport.iata_code, to_airport.iata_code, t.start_date, back, t.travelers.adults),
        note=note,
    )
