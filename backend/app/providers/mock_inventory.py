"""
Deterministic mock inventory (flights, hotels, trains, buses, activities).

Used for local development, tests and demos until partner credentials exist.
Results are seeded from the query so the same search returns the same offers.
Booking a traveler whose family_name is "FAIL" simulates a supplier failure.
"""

import random
import string
from datetime import datetime, time, timedelta, timezone

from app.common.fx import from_usd
from app.common.schemas import MediaImage, Money
from app.common.travel import (
    ActivityOffer,
    ActivitySearchRequest,
    BaseOffer,
    ContactInfo,
    FlightOffer,
    FlightSearchRequest,
    FlightSegment,
    FlightSlice,
    GroundSearchRequest,
    HotelOffer,
    HotelSearchRequest,
    OfferKind,
    ProviderBookingResult,
    TransportOffer,
    TravelerInfo,
)
from app.core.exceptions import ProviderError
from app.core.utils import stable_hash, utcnow
from app.providers.base import ActivityProvider, Airport, FlightProvider, GroundProvider, HotelProvider


AIRPORTS = [
    Airport(iata_code="DEL", name="Indira Gandhi International", city="New Delhi", country_code="IN"),
    Airport(iata_code="BOM", name="Chhatrapati Shivaji Maharaj International", city="Mumbai", country_code="IN"),
    Airport(iata_code="BLR", name="Kempegowda International", city="Bengaluru", country_code="IN"),
    Airport(iata_code="MAA", name="Chennai International", city="Chennai", country_code="IN"),
    Airport(iata_code="HYD", name="Rajiv Gandhi International", city="Hyderabad", country_code="IN"),
    Airport(iata_code="CCU", name="Netaji Subhas Chandra Bose International", city="Kolkata", country_code="IN"),
    Airport(iata_code="GOI", name="Goa International (Dabolim)", city="Goa", country_code="IN"),
    Airport(iata_code="GOX", name="Manohar International (Mopa)", city="Goa", country_code="IN"),
    Airport(iata_code="JAI", name="Jaipur International", city="Jaipur", country_code="IN"),
    Airport(iata_code="COK", name="Cochin International", city="Kochi", country_code="IN"),
    Airport(iata_code="DXB", name="Dubai International", city="Dubai", country_code="AE"),
    Airport(iata_code="SIN", name="Singapore Changi", city="Singapore", country_code="SG"),
    Airport(iata_code="BKK", name="Suvarnabhumi", city="Bangkok", country_code="TH"),
    Airport(iata_code="DPS", name="Ngurah Rai International", city="Bali", country_code="ID"),
    Airport(iata_code="LHR", name="Heathrow", city="London", country_code="GB"),
    Airport(iata_code="CDG", name="Charles de Gaulle", city="Paris", country_code="FR"),
    Airport(iata_code="FCO", name="Leonardo da Vinci–Fiumicino", city="Rome", country_code="IT"),
    Airport(iata_code="AMS", name="Schiphol", city="Amsterdam", country_code="NL"),
    Airport(iata_code="FRA", name="Frankfurt", city="Frankfurt", country_code="DE"),
    Airport(iata_code="JFK", name="John F. Kennedy International", city="New York", country_code="US"),
    Airport(iata_code="LAX", name="Los Angeles International", city="Los Angeles", country_code="US"),
    Airport(iata_code="SFO", name="San Francisco International", city="San Francisco", country_code="US"),
    Airport(iata_code="HND", name="Haneda", city="Tokyo", country_code="JP"),
    Airport(iata_code="NRT", name="Narita International", city="Tokyo", country_code="JP"),
    Airport(iata_code="SYD", name="Sydney Kingsford Smith", city="Sydney", country_code="AU"),
]

AIRLINES = [("IndiGo", "6E"), ("Air India", "AI"), ("Akasa Air", "QP"), ("Emirates", "EK"), ("Qatar Airways", "QR"), ("Lufthansa", "LH"), ("Singapore Airlines", "SQ")]


def _rng(*parts) -> random.Random:
    return random.Random(stable_hash(parts))


def _price(usd: float, currency: str) -> Money:
    return Money(amount=from_usd(usd, currency), currency=currency.upper())


def _ref(prefix: str) -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _expiry() -> datetime:
    return utcnow() + timedelta(minutes=30)


def _at(day, hour: int, minute: int) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)


class _MockBookingMixin:
    name = "mock"

    async def book(self, offer: BaseOffer, travelers: list[TravelerInfo], contact: ContactInfo) -> ProviderBookingResult:
        if any(t.family_name.upper() == "FAIL" for t in travelers):
            raise ProviderError("Supplier rejected the booking (simulated)", code="supplier_rejected")
        ref = _ref("MCK")
        tickets = [f"{ref}-{i + 1}" for i in range(len(travelers))] if offer.kind != OfferKind.hotel else []
        return ProviderBookingResult(provider_reference=ref, status="confirmed", tickets=tickets, message="Mock booking confirmed", raw={"mock": True})

    async def cancel(self, provider_reference: str, provider_data: dict) -> bool:
        return True


class MockFlightProvider(_MockBookingMixin, FlightProvider):
    async def suggest_airports(self, query: str, limit: int = 8) -> list[Airport]:
        q = query.strip().lower()
        return [a for a in AIRPORTS if q in a.iata_code.lower() or q in a.city.lower() or q in a.name.lower()][:limit]

    def _slice(self, rng: random.Random, origin: str, destination: str, day) -> tuple[FlightSlice, str, str]:
        airline, code = rng.choice(AIRLINES)
        stops = rng.choice([0, 0, 0, 1])
        dep = _at(day, rng.randint(5, 21), rng.choice([0, 15, 30, 45]))
        duration = rng.randint(80, 600) + stops * 90
        arr = dep + timedelta(minutes=duration)
        segments = []
        if stops == 0:
            segments.append(FlightSegment(carrier=airline, carrier_code=code, flight_number=f"{code}{rng.randint(100, 999)}", origin=origin, destination=destination, departure_at=dep, arrival_at=arr))
        else:
            via = rng.choice([a.iata_code for a in AIRPORTS if a.iata_code not in (origin, destination)])
            mid = dep + timedelta(minutes=duration // 2 - 45)
            segments.append(FlightSegment(carrier=airline, carrier_code=code, flight_number=f"{code}{rng.randint(100, 999)}", origin=origin, destination=via, departure_at=dep, arrival_at=mid))
            segments.append(FlightSegment(carrier=airline, carrier_code=code, flight_number=f"{code}{rng.randint(100, 999)}", origin=via, destination=destination, departure_at=mid + timedelta(minutes=90), arrival_at=arr))
        return FlightSlice(origin=origin, destination=destination, departure_at=dep, arrival_at=arr, duration_minutes=duration, stops=stops, segments=segments), airline, code

    async def search(self, req: FlightSearchRequest) -> list[FlightOffer]:
        rng = _rng("flight", req.model_dump(mode="json"))
        pax = req.adults + req.children + req.infants
        offers = []
        for i in range(min(req.max_results, 8)):
            out, airline, _ = self._slice(rng, req.origin, req.destination, req.departure_date)
            slices = [out]
            if req.return_date:
                back, _, _ = self._slice(rng, req.destination, req.origin, req.return_date)
                slices.append(back)
            if req.non_stop_only and any(s.stops for s in slices):
                continue
            cabin_mult = {"economy": 1, "premium_economy": 1.6, "business": 3.2, "first": 5}[req.cabin_class.value]
            usd = rng.uniform(70, 450) * len(slices) * cabin_mult * pax
            offers.append(
                FlightOffer(
                    offer_id=f"mock:fl_{stable_hash([req.model_dump(mode='json'), i])[:16]}",
                    provider="mock",
                    title=f"{airline} {out.origin}→{out.destination}" + (" (return)" if req.return_date else ""),
                    price=_price(usd, req.currency),
                    refundable=rng.random() > 0.6,
                    expires_at=_expiry(),
                    slices=slices,
                    cabin_class=req.cabin_class,
                    passengers=pax,
                    baggage="15kg check-in, 7kg cabin",
                )
            )
        return sorted(offers, key=lambda o: o.price.amount)


HOTEL_NAMES = ["Grand {c} Palace", "{c} Boutique Stay", "The {c} Residency", "Hostel {c} Central", "{c} Bay Resort & Spa", "Heritage Haveli {c}", "Urban Nest {c}"]
AMENITIES = ["Free WiFi", "Pool", "Breakfast", "Airport shuttle", "Spa", "Gym", "Parking", "Restaurant", "Bar", "Air conditioning"]


class MockHotelProvider(_MockBookingMixin, HotelProvider):
    async def search(self, req: HotelSearchRequest) -> list[HotelOffer]:
        rng = _rng("hotel", req.model_dump(mode="json"))
        offers = []
        for i, template in enumerate(HOTEL_NAMES[: req.max_results]):
            name = template.format(c=req.city.title())
            stars = rng.choice([2, 3, 3, 4, 4, 5])
            per_night_usd = stars * rng.uniform(18, 45) * req.rooms
            per_night = _price(per_night_usd, req.currency)
            if req.max_price_per_night and per_night.amount > req.max_price_per_night:
                continue
            if req.min_rating and stars < req.min_rating:
                continue
            slug = name.lower().replace(" ", "-")
            offers.append(
                HotelOffer(
                    offer_id=f"mock:ht_{stable_hash([req.model_dump(mode='json'), i])[:16]}",
                    provider="mock",
                    title=name,
                    hotel_id=f"mockhotel_{i}",
                    name=name,
                    address=f"{rng.randint(1, 200)} Main Road, {req.city.title()}",
                    city=req.city.title(),
                    star_rating=stars,
                    review_score=round(rng.uniform(7.0, 9.6), 1),
                    images=[MediaImage(url=f"https://picsum.photos/seed/{slug}/800/600", thumbnail_url=f"https://picsum.photos/seed/{slug}/320/240", alt=name, source="mock")],
                    room_name=rng.choice(["Deluxe Double", "Superior King", "Standard Twin", "Family Suite"]),
                    board_type=rng.choice(["room_only", "breakfast_included"]),
                    check_in=req.check_in,
                    check_out=req.check_out,
                    nights=req.nights,
                    price_per_night=per_night,
                    price=Money(amount=round(per_night.amount * req.nights, 2), currency=per_night.currency),
                    amenities=rng.sample(AMENITIES, 5),
                    refundable=rng.random() > 0.4,
                    cancellation_policy="Free cancellation until 48h before check-in" if stars > 2 else "Non-refundable",
                    expires_at=_expiry(),
                )
            )
        return sorted(offers, key=lambda o: o.price.amount)


TRAINS = [("Rajdhani Express", "12951", ["1A", "2A", "3A"]), ("Shatabdi Express", "12015", ["CC", "EC"]), ("Vande Bharat Express", "22435", ["CC", "EC"]), ("Duronto Express", "12213", ["2A", "3A", "SL"]), ("Superfast Mail", "12391", ["SL", "3A", "2A"])]
BUS_OPERATORS = [("IntrCity SmartBus", ["AC Sleeper", "AC Seater"]), ("Zingbus", ["AC Sleeper"]), ("VRL Travels", ["Volvo AC Seater", "Non-AC Sleeper"]), ("State Transport", ["Ordinary", "AC Seater"])]


class MockGroundProvider(_MockBookingMixin, GroundProvider):
    async def search(self, mode: OfferKind, req: GroundSearchRequest) -> list[TransportOffer]:
        rng = _rng(mode.value, req.model_dump(mode="json"))
        offers = []
        options = TRAINS if mode == OfferKind.train else BUS_OPERATORS
        for i in range(min(req.max_results, 6)):
            dep = _at(req.date, rng.randint(0, 22), rng.choice([0, 10, 20, 30, 40, 50]))
            duration = rng.randint(240, 960)
            if mode == OfferKind.train:
                name, number, classes = options[i % len(options)]
                operator, service_name = "Indian Railways", name
                number = str(int(number) + i)
            else:
                operator, classes = options[i % len(options)]
                service_name, number = f"{operator} {req.origin.title()}–{req.destination.title()}", f"BUS{rng.randint(1000, 9999)}"
            travel_class = req.travel_class if req.travel_class in classes else classes[0]
            base_usd = (rng.uniform(4, 30) if mode == OfferKind.bus else rng.uniform(6, 60)) * req.passengers
            offers.append(
                TransportOffer(
                    offer_id=f"mock:{mode.value[:2]}_{stable_hash([req.model_dump(mode='json'), mode.value, i])[:16]}",
                    kind=mode,
                    provider="mock",
                    title=f"{service_name} ({travel_class})",
                    operator=operator,
                    service_number=number,
                    service_name=service_name,
                    origin=req.origin.title(),
                    destination=req.destination.title(),
                    departure_at=dep,
                    arrival_at=dep + timedelta(minutes=duration),
                    duration_minutes=duration,
                    travel_class=travel_class,
                    seats_available=rng.randint(0, 60),
                    amenities=rng.sample(["Charging point", "Water bottle", "Blanket", "Meals", "WiFi", "Live tracking"], 3),
                    price=_price(base_usd, req.currency),
                    refundable=True,
                    expires_at=_expiry(),
                )
            )
        return sorted(offers, key=lambda o: o.departure_at)


ACTIVITIES = ["Old Town Walking Tour", "Street Food Tasting Tour", "Sunset Boat Cruise", "Cooking Class with a Local Chef", "Museum Skip-the-Line Ticket", "Day Trip to the Countryside", "Night Market Experience", "Sunrise Hike & Photography"]


class MockActivityProvider(_MockBookingMixin, ActivityProvider):
    async def search(self, req: ActivitySearchRequest) -> list[ActivityOffer]:
        rng = _rng("activity", req.model_dump(mode="json"))
        names = [a for a in ACTIVITIES if not req.query or any(w in a.lower() for w in req.query.lower().split())] or ACTIVITIES
        offers = []
        for i, base in enumerate(names[: req.max_results]):
            name = f"{req.destination.title()}: {base}"
            slug = name.lower().replace(" ", "-").replace(":", "")
            offers.append(
                ActivityOffer(
                    offer_id=f"mock:ac_{stable_hash([req.model_dump(mode='json'), i])[:16]}",
                    provider="mock",
                    title=name,
                    product_code=f"MOCK{i:03d}",
                    name=name,
                    description=f"A highly rated {base.lower()} in {req.destination.title()} led by local guides.",
                    duration_minutes=rng.choice([90, 120, 180, 240, 480]),
                    rating=round(rng.uniform(4.2, 4.9), 1),
                    review_count=rng.randint(40, 4000),
                    images=[MediaImage(url=f"https://picsum.photos/seed/{slug}/800/600", alt=name, source="mock")],
                    date=req.date,
                    price=_price(rng.uniform(12, 120), req.currency),
                    refundable=True,
                    expires_at=_expiry(),
                )
            )
        return offers
