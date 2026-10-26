"""
City -> airport resolution from the offline `airportsdata` dataset (no API calls).

Strategy: given a geocoded city, prefer the nearest airport with "International" in its
name within 150 km, otherwise the nearest airport with an IATA code within 100 km.
"""

import math
from functools import lru_cache

from app.providers.base import Airport

INTERNATIONAL_RADIUS_KM = 150
ANY_RADIUS_KM = 100


@lru_cache(maxsize=1)
def _airports() -> list[dict]:
    import airportsdata

    return [a for a in airportsdata.load("IATA").values() if a.get("iata") and a.get("lat") is not None]


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _to_airport(a: dict) -> Airport:
    return Airport(iata_code=a["iata"], name=a["name"], city=a.get("city") or "", country_code=a.get("country") or "")


def by_code(code: str) -> Airport | None:
    code = code.strip().upper()
    for a in _airports():
        if a["iata"] == code:
            return _to_airport(a)
    return None


def nearest(lat: float, lng: float) -> Airport | None:
    ranked = sorted(((_km(lat, lng, a["lat"], a["lon"]), a) for a in _airports()), key=lambda x: x[0])
    for dist, a in ranked:
        if dist > INTERNATIONAL_RADIUS_KM:
            break
        if "international" in a["name"].lower():
            return _to_airport(a)
    if ranked and ranked[0][0] <= ANY_RADIUS_KM:
        return _to_airport(ranked[0][1])
    return None


def search(query: str, limit: int = 8) -> list[Airport]:
    """Text search over code, city, state and name.

    Ranking: exact city/state name ("Goa" -> GOI/GOX, not Genoa's GOA), then exact IATA code,
    then partial matches; international airports first within each group.
    """
    q = query.strip().lower()
    if not q:
        return []

    def place(a: dict) -> tuple[str, str]:
        return (a.get("city") or "").lower(), (a.get("subd") or "").lower()

    hits = [
        a for a in _airports()
        if q == a["iata"].lower() or q in place(a)[0] or q == place(a)[1] or q in a["name"].lower()
    ]

    def rank(a: dict) -> tuple:
        city, subd = place(a)
        group = 0 if q in (city, subd) else 1 if q == a["iata"].lower() else 2
        return (group, "international" not in a["name"].lower(), a["name"])

    hits.sort(key=rank)
    return [_to_airport(a) for a in hits[:limit]]
