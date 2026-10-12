"""Real provider integrations, exercised against mocked HTTP (httpx.MockTransport)."""

import json
from datetime import date, timedelta

import httpx
import pytest

from app.common.schemas import WeatherCode
from app.common.travel import ContactInfo, FlightSearchRequest, HotelSearchRequest, TravelerInfo
from app.core.exceptions import AppError, ProviderError
from app.providers.duffel import DuffelFlightProvider, parse_iso_duration
from app.providers.liteapi import LiteApiHotelProvider
from app.providers.llm import OllamaLLM
from app.providers.media import WikipediaImageProvider, YouTubeDataProvider, maps_url
from app.providers.speech import DeepgramSpeechProvider, MockSpeechProvider
from app.providers.weather import OpenMeteoProvider, clamp_forecast_window, wmo_to_condition
from app.modules.planner.schemas import HotelsDraft

D = (date.today() + timedelta(days=20)).isoformat()


def client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


DUFFEL_OFFER = {
    "id": "off_123",
    "total_amount": "250.40",
    "total_currency": "USD",
    "expires_at": "2099-01-01T00:00:00Z",
    "owner": {"name": "Air India", "iata_code": "AI", "logo_symbol_url": "https://logo"},
    "conditions": {"refund_before_departure": {"allowed": True}},
    "passengers": [{"id": "pas_1"}],
    "slices": [{
        "origin": {"iata_code": "DEL"}, "destination": {"iata_code": "BOM"}, "duration": "PT2H10M",
        "segments": [{
            "marketing_carrier": {"name": "Air India", "iata_code": "AI"}, "marketing_carrier_flight_number": "865",
            "origin": {"iata_code": "DEL"}, "destination": {"iata_code": "BOM"},
            "departing_at": f"{D}T06:00:00", "arriving_at": f"{D}T08:10:00", "aircraft": {"name": "A320neo"},
        }],
    }],
}


def test_iso_duration():
    assert parse_iso_duration("PT2H10M") == 130
    assert parse_iso_duration("P1DT2H") == 1560
    assert parse_iso_duration(None) == 0


async def test_duffel_search_quote_book_cancel():
    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path))
        assert request.headers["Duffel-Version"] == "v2"
        assert request.headers["Authorization"] == "Bearer tok"
        if request.url.path == "/air/offer_requests":
            body = json.loads(request.content)
            assert body["data"]["max_connections"] == 0
            assert body["data"]["passengers"] == [{"type": "adult"}]
            return httpx.Response(201, json={"data": {"offers": [DUFFEL_OFFER]}})
        if request.url.path == "/air/offers/off_123":
            return httpx.Response(200, json={"data": DUFFEL_OFFER})
        if request.url.path == "/air/orders":
            pax = json.loads(request.content)["data"]["passengers"][0]
            assert pax["id"] == "pas_1" and pax["born_on"] == "1990-05-01"
            return httpx.Response(201, json={"data": {"id": "ord_9", "booking_reference": "ABC123", "documents": [{"unique_identifier": "098-123"}]}})
        if request.url.path == "/air/order_cancellations":
            return httpx.Response(201, json={"data": {"id": "ore_1"}})
        if request.url.path == "/air/order_cancellations/ore_1/actions/confirm":
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(404, json={"errors": [{"message": "nope"}]})

    async with client_for(handler) as http:
        p = DuffelFlightProvider(http, "tok")
        offers = await p.search(FlightSearchRequest(origin="DEL", destination="BOM", departure_date=D, non_stop_only=True))
        o = offers[0]
        assert o.offer_id == "duffel:off_123" and o.price.amount == 250.40 and o.refundable
        assert o.slices[0].duration_minutes == 130 and o.slices[0].segments[0].flight_number == "AI865"
        quoted = await p.quote(o)
        assert quoted.price.amount == 250.40
        traveler = TravelerInfo(title="mr", given_name="R", family_name="K", born_on="1990-05-01", gender="m")
        result = await p.book(o, [traveler], ContactInfo(email="a@b.co", phone="+911234567"))
        assert result.provider_reference == "ABC123" and result.raw["order_id"] == "ord_9" and result.tickets == ["098-123"]
        assert await p.cancel("ABC123", result.raw)
        with pytest.raises(ProviderError):
            await p.book(o, [TravelerInfo(given_name="R", family_name="K")], ContactInfo(email="a@b.co", phone="+911234567"))


async def test_duffel_error_surfaces_message():
    async with client_for(lambda r: httpx.Response(422, json={"errors": [{"message": "Invalid origin"}]})) as http:
        with pytest.raises(ProviderError, match="Invalid origin"):
            await DuffelFlightProvider(http, "tok").search(FlightSearchRequest(origin="XXX", destination="BOM", departure_date=D))


async def test_liteapi_search_and_country_required():
    checkout = (date.fromisoformat(D) + timedelta(days=2)).isoformat()
    payload = {
        "data": [{"hotelId": "lp1", "roomTypes": [
            {"offerId": "OF-A", "offerRetailRate": {"amount": 300, "currency": "USD"}, "rates": [{"name": "Deluxe", "boardName": "Breakfast Included", "cancellationPolicies": {"refundableTag": "RFN"}}]},
            {"offerId": "OF-B", "offerRetailRate": {"amount": 200, "currency": "USD"}, "rates": [{"name": "Std", "boardName": "Room Only", "cancellationPolicies": {"refundableTag": "NRFN"}}]},
        ]}],
        "hotels": [{"id": "lp1", "name": "Sea View", "main_photo": "https://img", "address": "Beach Rd", "rating": 8.7, "stars": 4}],
    }

    def handler(request):
        assert request.headers["X-API-Key"] == "k"
        body = json.loads(request.content)
        assert body["countryCode"] == "IN" and body["occupancies"] == [{"adults": 2, "children": []}]
        return httpx.Response(200, json=payload)

    async with client_for(handler) as http:
        p = LiteApiHotelProvider(http, "k")
        offers = await p.search(HotelSearchRequest(city="Goa", country_code="in", check_in=D, check_out=checkout))
        h = offers[0]
        assert h.offer_id == "liteapi:OF-B" and h.price.amount == 200 and h.price_per_night.amount == 100
        assert h.name == "Sea View" and h.images[0].url == "https://img" and h.refundable is False
        with pytest.raises(AppError):
            await p.search(HotelSearchRequest(city="Goa", check_in=D, check_out=checkout))


async def test_open_meteo_geocode_and_forecast():
    def handler(request):
        if "geocoding" in request.url.host:
            return httpx.Response(200, json={"results": [{"name": "Goa", "latitude": 15.3, "longitude": 74.1, "country": "India", "country_code": "IN", "admin1": "Goa", "timezone": "Asia/Kolkata"}]})
        params = request.url.params
        assert params["daily"].startswith("weather_code") and params["timezone"] == "auto"
        return httpx.Response(200, json={"daily": {"time": [params["start_date"]], "weather_code": [61], "temperature_2m_max": [31.2], "temperature_2m_min": [24.0], "precipitation_sum": [5.5], "precipitation_probability_max": [80]}})

    async with client_for(handler) as http:
        p = OpenMeteoProvider(http)
        place = (await p.geocode("goa"))[0]
        assert place.country_code == "IN" and place.lat == 15.3
        days = await p.forecast(place.lat, place.lng, date.today(), date.today() + timedelta(days=3))
        assert days[0].condition == WeatherCode.rain and days[0].temp_max_c == 31.2
        assert await p.forecast(1, 1, date.today() + timedelta(days=60), date.today() + timedelta(days=62)) == []


def test_weather_helpers():
    assert wmo_to_condition(0) == WeatherCode.clear and wmo_to_condition(95) == WeatherCode.storm and wmo_to_condition(None) == WeatherCode.unknown
    today = date.today()
    assert clamp_forecast_window(today - timedelta(days=3), today + timedelta(days=2)) == (today, today + timedelta(days=2))
    assert clamp_forecast_window(today + timedelta(days=40), today + timedelta(days=45)) is None


async def test_wikipedia_images_and_failure_is_soft():
    def handler(request):
        assert "NomadIQ" in request.headers["User-Agent"]
        return httpx.Response(200, json={"query": {"pages": [
            {"index": 2, "title": "B", "fullurl": "https://w/B"},
            {"index": 3, "title": "Rajasthan", "fullurl": "https://w/R", "thumbnail": {"source": "https://up/thumb/b/1280px-Rajasthan_locator_map.svg.png"}},
            {"index": 1, "title": "Taj Mahal", "fullurl": "https://w/T", "thumbnail": {"source": "https://up/thumb/a/1280px-Taj.jpg", "width": 1280, "height": 853}},
        ]}})

    async with client_for(handler) as http:
        imgs = await WikipediaImageProvider(http).search("Taj Mahal", 3)
        assert len(imgs) == 1 and imgs[0].url == "https://up/thumb/a/1280px-Taj.jpg" and imgs[0].source_url == "https://w/T"
        assert imgs[0].thumbnail_url == "https://up/thumb/a/500px-Taj.jpg"
    async with client_for(lambda r: httpx.Response(503)) as http:
        assert await WikipediaImageProvider(http).search("x") == []


async def test_youtube_api_and_fallback():
    def ok(request):
        return httpx.Response(200, json={"items": [{"id": {"videoId": "abc"}, "snippet": {"title": "Goa Guide", "channelTitle": "Ch", "thumbnails": {"medium": {"url": "https://t"}}}}]})

    async with client_for(ok) as http:
        vids = await YouTubeDataProvider(http, "key").search("goa")
        assert vids[0].url == "https://www.youtube.com/watch?v=abc" and vids[0].channel == "Ch"
    async with client_for(lambda r: httpx.Response(403)) as http:
        fallback = await YouTubeDataProvider(http, "key").search("goa beaches")
        assert fallback[0].url == "https://www.youtube.com/results?search_query=goa+beaches"


async def test_deepgram_and_mock_speech():
    def handler(request):
        assert request.headers["Authorization"] == "Token dg" and request.url.params["model"] == "nova-3"
        return httpx.Response(200, json={"metadata": {"duration": 3.2}, "results": {"channels": [{"detected_language": "hi", "alternatives": [{"transcript": "goa ki flight", "confidence": 0.93}]}]}})

    async with client_for(handler) as http:
        t = await DeepgramSpeechProvider(http, "dg").transcribe(b"\x00\x01", "audio/webm")
        assert t.text == "goa ki flight" and t.language == "hi" and t.duration_seconds == 3.2
    assert (await MockSpeechProvider().transcribe(b"\xff\xfe\x00", "audio/wav")).text == "Plan a 3 day trip to Goa"


async def test_ollama_structured_output_request():
    def handler(request):
        body = json.loads(request.content)
        assert body["format"]["type"] == "object" and body["stream"] is False
        assert body["messages"][0]["role"] == "system" and "SCHEMA" in body["messages"][0]["content"]
        return httpx.Response(200, json={"message": {"content": '{"hotels": [{"name": "Taj Exotica", "price_per_night": 220}]}'}})

    async with client_for(handler) as http:
        draft = await OllamaLLM(http, "http://ollama", "llama3.1", 10).generate_json("p", HotelsDraft)
        assert draft.hotels[0].name == "Taj Exotica"
    async with client_for(lambda r: httpx.Response(500)) as http:
        with pytest.raises(ProviderError) as exc:
            await OllamaLLM(http, "http://ollama", "m", 10).generate("p")
        assert exc.value.code == "llm_unavailable"


def test_maps_url():
    assert maps_url("Baga Beach", "", "Goa") == "https://www.google.com/maps/search/?api=1&query=Baga+Beach%2C+Goa"
