"""Builds the provider set from settings. Stored on `app.state.providers`."""

from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.core.exceptions import GoneError
from app.providers.base import ActivityProvider, FlightProvider, GroundProvider, HotelProvider, InventoryProvider
from app.providers.llm import GeminiLLM, LLMProvider, MockLLM, OllamaLLM
from app.providers.media import (
    ImageProvider,
    KnowledgeProvider,
    MockImageProvider,
    MockKnowledgeProvider,
    MockVideoProvider,
    PexelsImageProvider,
    UnsplashImageProvider,
    VideoProvider,
    WikipediaImageProvider,
    WikipediaKnowledgeProvider,
    YouTubeDataProvider,
    YouTubeLinkProvider,
)
from app.providers.mock_inventory import MockActivityProvider, MockFlightProvider, MockGroundProvider, MockHotelProvider
from app.providers.payments import MockPaymentProvider, PaymentProvider
from app.providers.speech import DeepgramSpeechProvider, MockSpeechProvider, OpenAISpeechProvider, SpeechProvider
from app.providers.weather import MockWeatherProvider, OpenMeteoProvider, WeatherProvider


@dataclass
class Providers:
    llm: LLMProvider
    flights: FlightProvider
    hotels: HotelProvider
    ground: GroundProvider
    activities: ActivityProvider
    images: ImageProvider
    videos: VideoProvider
    knowledge: KnowledgeProvider
    weather: WeatherProvider
    speech: SpeechProvider
    payments: PaymentProvider

    def inventory_for(self, provider_name: str, kind: str) -> InventoryProvider:
        """Route a booking to the provider instance that issued the offer."""
        by_kind: dict[str, InventoryProvider] = {
            "flight": self.flights,
            "hotel": self.hotels,
            "train": self.ground,
            "bus": self.ground,
            "activity": self.activities,
        }
        provider = by_kind[kind]
        if provider.name != provider_name:
            raise GoneError("This offer came from a provider that is no longer active; search again", code="offer_expired")
        return provider


def build_providers(settings: Settings, http: httpx.AsyncClient) -> Providers:
    llm: LLMProvider
    if settings.llm_provider == "gemini":
        llm = GeminiLLM(settings.google_api_key, settings.gemini_model)
    elif settings.llm_provider == "ollama":
        llm = OllamaLLM(http, settings.ollama_base_url, settings.ollama_model, settings.llm_timeout_seconds)
    else:
        llm = MockLLM()

    if settings.flight_provider == "duffel":
        from app.providers.duffel import DuffelFlightProvider

        flights: FlightProvider = DuffelFlightProvider(http, settings.duffel_api_token)
    else:
        flights = MockFlightProvider()

    if settings.hotel_provider == "liteapi":
        from app.providers.liteapi import LiteApiHotelProvider

        hotels: HotelProvider = LiteApiHotelProvider(http, settings.liteapi_api_key)
    else:
        hotels = MockHotelProvider()

    images: ImageProvider = {
        "wikipedia": lambda: WikipediaImageProvider(http),
        "unsplash": lambda: UnsplashImageProvider(http, settings.unsplash_access_key),
        "pexels": lambda: PexelsImageProvider(http, settings.pexels_api_key),
        "mock": MockImageProvider,
    }[settings.image_provider]()

    videos: VideoProvider = {
        "youtube": lambda: YouTubeDataProvider(http, settings.youtube_api_key),
        "youtube_link": YouTubeLinkProvider,
        "mock": MockVideoProvider,
    }[settings.video_provider]()

    knowledge: KnowledgeProvider = WikipediaKnowledgeProvider(http) if settings.knowledge_provider == "wikipedia" else MockKnowledgeProvider()
    weather: WeatherProvider = OpenMeteoProvider(http) if settings.weather_provider == "open_meteo" else MockWeatherProvider()

    speech: SpeechProvider = {
        "deepgram": lambda: DeepgramSpeechProvider(http, settings.deepgram_api_key),
        "openai": lambda: OpenAISpeechProvider(http, settings.openai_api_key),
        "mock": MockSpeechProvider,
    }[settings.speech_provider]()

    return Providers(
        llm=llm,
        flights=flights,
        hotels=hotels,
        ground=MockGroundProvider(),
        activities=MockActivityProvider(),
        images=images,
        videos=videos,
        knowledge=knowledge,
        weather=weather,
        speech=speech,
        payments=MockPaymentProvider(),
    )
