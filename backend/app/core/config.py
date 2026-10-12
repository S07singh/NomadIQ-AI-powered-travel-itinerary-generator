"""
Application settings loaded from environment variables / .env.

Every external integration is selected by a `*_PROVIDER` variable so the same
code runs fully offline (mock providers) for tests and against real APIs in
production.
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-only-change-me-dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ─── App ──────────────────────────────────────────────
    app_name: str = "NomadIQ API"
    app_version: str = "2.0.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8081", "http://localhost:19006"]
    public_web_url: str = "http://localhost:3000"
    log_level: str = "INFO"
    min_mobile_app_version: str = "1.0.0"

    # ─── Database ─────────────────────────────────────────
    # Local:  mongodb://127.0.0.1:27017
    # Atlas:  mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_db: str = "nomadiq"

    # ─── Auth ─────────────────────────────────────────────
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 30
    rate_limit_auth_per_minute: int = 10

    # ─── LLM ──────────────────────────────────────────────
    llm_provider: Literal["mock", "ollama", "gemini"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: float = 180.0

    # ─── Booking providers ────────────────────────────────
    flight_provider: Literal["mock", "duffel"] = "mock"
    duffel_api_token: str = ""
    hotel_provider: Literal["mock", "liteapi"] = "mock"
    liteapi_api_key: str = ""
    ground_provider: Literal["mock"] = "mock"
    activity_provider: Literal["mock"] = "mock"
    payment_provider: Literal["mock"] = "mock"
    offer_ttl_minutes: int = 30

    # ─── Media / live data ────────────────────────────────
    image_provider: Literal["mock", "wikipedia", "unsplash", "pexels"] = "wikipedia"
    unsplash_access_key: str = ""
    pexels_api_key: str = ""
    video_provider: Literal["mock", "youtube_link", "youtube"] = "youtube_link"
    youtube_api_key: str = ""
    weather_provider: Literal["mock", "open_meteo"] = "open_meteo"  # also used for geocoding
    knowledge_provider: Literal["mock", "wikipedia"] = "wikipedia"

    # ─── Voice ────────────────────────────────────────────
    speech_provider: Literal["mock", "deepgram", "openai"] = "mock"
    deepgram_api_key: str = ""
    openai_api_key: str = ""
    max_audio_bytes: int = 10 * 1024 * 1024

    # ─── Performance ──────────────────────────────────────
    http_timeout_seconds: float = 15.0
    search_cache_ttl_seconds: int = 300
    content_cache_ttl_seconds: int = 6 * 3600

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be set to a strong value (>= 32 chars) in production")
            if self.llm_provider == "mock":
                raise ValueError("LLM_PROVIDER=mock is not allowed in production")
        return self

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
