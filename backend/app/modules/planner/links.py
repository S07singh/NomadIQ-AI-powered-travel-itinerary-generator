"""Deep links to booking sites, so every flight and hotel in a plan has somewhere to book."""

from datetime import date
from urllib.parse import quote, quote_plus

from app.common.schemas import ExternalLink


def google_flights_link(origin: str, destination: str, depart: date, back: date | None = None) -> str:
    text = f"Flights from {origin} to {destination} on {depart.isoformat()}"
    if back:
        text += f" through {back.isoformat()}"
    return f"https://www.google.com/travel/flights?q={quote_plus(text)}"


def kayak_flights_link(origin: str, destination: str, depart: date, back: date | None = None, adults: int = 1) -> str:
    url = f"https://www.kayak.com/flights/{origin}-{destination}/{depart.isoformat()}"
    if back:
        url += f"/{back.isoformat()}"
    return f"{url}/{adults}adults?sort=price_a"


def flight_links(origin: str, destination: str, depart: date, back: date | None, adults: int) -> list[ExternalLink]:
    return [
        ExternalLink(label="Google Flights", url=google_flights_link(origin, destination, depart, back)),
        ExternalLink(label="Kayak", url=kayak_flights_link(origin, destination, depart, back, adults)),
    ]


def hotel_links(name: str, city: str, check_in: date | None, check_out: date | None, adults: int, rooms: int) -> list[ExternalLink]:
    where = f"{name}, {city}"
    booking = f"https://www.booking.com/searchresults.html?ss={quote_plus(where)}&group_adults={adults}&no_rooms={rooms}"
    if check_in and check_out:
        booking += f"&checkin={check_in.isoformat()}&checkout={check_out.isoformat()}"
    links = [
        ExternalLink(label="Booking.com", url=booking),
        ExternalLink(label="Google Hotels", url=f"https://www.google.com/travel/search?q={quote_plus(where)}"),
    ]
    if check_in and check_out:
        links.append(
            ExternalLink(label="Kayak", url=f"https://www.kayak.com/hotels/{quote(city)}/{check_in.isoformat()}/{check_out.isoformat()}/{adults}adults?sort=price_a")
        )
    return links
