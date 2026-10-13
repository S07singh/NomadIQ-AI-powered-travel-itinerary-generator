"""Health checks + client bootstrap config (enums, feature flags, forced-update version)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.common.schemas import APIModel, TravelStyle, TripPace, Vibe
from app.common.travel import CabinClass, OfferKind
from app.core.database import get_db
from app.core.deps import JobsDep, ProvidersDep, SettingsDep
from app.core.utils import utcnow

router = APIRouter(tags=["Meta"])


class ClientConfig(APIModel):
    app_name: str
    api_version: str
    min_mobile_app_version: str
    enums: dict[str, list[str]]
    features: dict[str, bool]
    providers: dict[str, str]


@router.get("/health", summary="Liveness probe")
async def health():
    return {"status": "ok", "time": utcnow().isoformat()}


@router.get("/health/ready", summary="Readiness probe (checks MongoDB)")
async def ready(jobs: JobsDep):
    try:
        await get_db().command("ping")
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "unavailable", "mongo": str(exc)[:200]})
    return {"status": "ready", "mongo": "ok", "active_jobs": jobs.active}


@router.get("/meta/config", response_model=ClientConfig, summary="Bootstrap config for web & mobile clients")
async def client_config(settings: SettingsDep, providers: ProvidersDep) -> ClientConfig:
    return ClientConfig(
        app_name=settings.app_name,
        api_version=settings.app_version,
        min_mobile_app_version=settings.min_mobile_app_version,
        enums={
            "travel_styles": [e.value for e in TravelStyle],
            "paces": [e.value for e in TripPace],
            "vibes": [e.value for e in Vibe],
            "cabin_classes": [e.value for e in CabinClass],
            "offer_kinds": [e.value for e in OfferKind],
        },
        features={
            "voice": True,
            "assistant": True,
            "live_flights": providers.flights.name != "mock",
            "live_hotels": providers.hotels.name != "mock",
            "live_trains": providers.ground.name != "mock",
            "live_buses": providers.ground.name != "mock",
            "live_activities": providers.activities.name != "mock",
            "in_app_payments": providers.payments.name != "mock",
        },
        providers={
            "llm": providers.llm.name,
            "flights": providers.flights.name,
            "hotels": providers.hotels.name,
            "images": providers.images.name,
            "videos": providers.videos.name,
            "speech": providers.speech.name,
        },
    )
