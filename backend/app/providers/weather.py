"""
Geocoding + weather. Open-Meteo is free, key-less and fast (<10 ms server time);
commercial use above 10k req/day needs their paid plan.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta

import httpx
from loguru import logger

from app.common.schemas import Place, WeatherCode, WeatherDay

FORECAST_HORIZON_DAYS = 15


def wmo_to_condition(code: int | None) -> WeatherCode:
    if code is None:
        return WeatherCode.unknown
    if code == 0:
        return WeatherCode.clear
    if code in (1, 2):
        return WeatherCode.partly_cloudy
    if code == 3:
        return WeatherCode.cloudy
    if code in (45, 48):
        return WeatherCode.fog
    if 51 <= code <= 57:
        return WeatherCode.drizzle
    if 61 <= code <= 67 or 80 <= code <= 82:
        return WeatherCode.rain
    if 71 <= code <= 77 or code in (85, 86):
        return WeatherCode.snow
    if code >= 95:
        return WeatherCode.storm
    return WeatherCode.unknown


def clamp_forecast_window(start: date, end: date) -> tuple[date, date] | None:
    """Open-Meteo forecasts ~16 days ahead; return the overlapping window or None."""
    today = date.today()
    horizon = today + timedelta(days=FORECAST_HORIZON_DAYS)
    start, end = max(start, today), min(end, horizon)
    return (start, end) if start <= end else None


class WeatherProvider(ABC):
    @abstractmethod
    async def geocode(self, query: str, limit: int = 5) -> list[Place]: ...

    @abstractmethod
    async def forecast(self, lat: float, lng: float, start: date, end: date) -> list[WeatherDay]: ...


MOCK_PLACES = {
    "goa": Place(name="Goa", country="India", country_code="IN", region="Goa", lat=15.2993, lng=74.124, timezone="Asia/Kolkata"),
    "paris": Place(name="Paris", country="France", country_code="FR", region="Île-de-France", lat=48.8566, lng=2.3522, timezone="Europe/Paris"),
    "tokyo": Place(name="Tokyo", country="Japan", country_code="JP", region="Tokyo", lat=35.6762, lng=139.6503, timezone="Asia/Tokyo"),
    "jaipur": Place(name="Jaipur", country="India", country_code="IN", region="Rajasthan", lat=26.9124, lng=75.7873, timezone="Asia/Kolkata"),
}


class MockWeatherProvider(WeatherProvider):
    async def geocode(self, query: str, limit: int = 5) -> list[Place]:
        q = query.strip().lower()
        hits = [p for k, p in MOCK_PLACES.items() if k.startswith(q) or q.startswith(k)]
        return hits[:limit] or [Place(name=query.title(), lat=20.0, lng=78.0, timezone="UTC")]

    async def forecast(self, lat: float, lng: float, start: date, end: date) -> list[WeatherDay]:
        window = clamp_forecast_window(start, end)
        if not window:
            return []
        days = (window[1] - window[0]).days + 1
        return [
            WeatherDay(date=window[0] + timedelta(days=i), temp_min_c=22 + i % 3, temp_max_c=31 + i % 4, precipitation_mm=0.0 if i % 3 else 2.5, precipitation_probability=10 if i % 3 else 60, condition=WeatherCode.clear if i % 3 else WeatherCode.rain)
            for i in range(days)
        ]


class OpenMeteoProvider(WeatherProvider):
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def geocode(self, query: str, limit: int = 5) -> list[Place]:
        try:
            resp = await self.http.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": query, "count": limit, "language": "en", "format": "json"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Geocoding failed for '{query}': {exc}")
            return []
        return [
            Place(
                name=r["name"],
                country=r.get("country"),
                country_code=r.get("country_code"),
                region=r.get("admin1"),
                lat=r["latitude"],
                lng=r["longitude"],
                timezone=r.get("timezone"),
                population=r.get("population"),
            )
            for r in resp.json().get("results", []) or []
        ]

    async def forecast(self, lat: float, lng: float, start: date, end: date) -> list[WeatherDay]:
        window = clamp_forecast_window(start, end)
        if not window:
            return []
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,sunrise,sunset",
            "timezone": "auto",
            "start_date": window[0].isoformat(),
            "end_date": window[1].isoformat(),
        }
        try:
            resp = await self.http.get("https://api.open-meteo.com/v1/forecast", params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Forecast failed for {lat},{lng}: {exc}")
            return []
        return parse_daily(resp.json().get("daily") or {})


def parse_daily(daily: dict) -> list[WeatherDay]:
    def col(name: str, i: int):
        values = daily.get(name) or []
        return values[i] if i < len(values) else None

    return [
        WeatherDay(
            date=day,
            temp_min_c=col("temperature_2m_min", i),
            temp_max_c=col("temperature_2m_max", i),
            precipitation_mm=col("precipitation_sum", i),
            precipitation_probability=col("precipitation_probability_max", i),
            condition=wmo_to_condition(col("weather_code", i)),
            sunrise=col("sunrise", i),
            sunset=col("sunset", i),
        )
        for i, day in enumerate(daily.get("time", []))
    ]
