"""
NomadIQ API — application factory.

One backend for the website (Next.js) and the mobile app (React Native / Expo):
versioned REST under /api/v1, bearer-token auth, JSON everywhere, SSE for live progress.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from app.core.config import Settings, get_settings
from app.core.database import close_mongo, connect_mongo
from app.core.exceptions import register_exception_handlers
from app.core.jobs import JobRunner
from app.core.logging import setup_logging
from app.core.utils import utcnow
from app.modules.assistant.router import router as assistant_router
from app.modules.assistant.router import voice_router
from app.modules.auth.router import router as auth_router
from app.modules.bookings.router import router as bookings_router
from app.modules.explore.router import router as explore_router
from app.modules.meta.router import router as meta_router
from app.modules.search.router import router as search_router
from app.modules.trips.router import router as trips_router
from app.modules.trips.router import shared_router
from app.modules.users.router import router as users_router
from app.providers.registry import Providers, build_providers

ROUTERS = [meta_router, auth_router, users_router, trips_router, shared_router, search_router, bookings_router, explore_router, assistant_router, voice_router]


async def recover_interrupted_trips(db) -> None:
    """Trips left mid-generation by a restart can never finish — mark them failed so users can retry."""
    result = await db["trips"].update_many(
        {"status": {"$in": ["queued", "generating"]}},
        {"$set": {"status": "failed", "error": "interrupted", "progress.status": "failed", "progress.message": "Planning was interrupted. Tap regenerate.", "updated_at": utcnow()}},
    )
    if result.modified_count:
        logger.warning(f"Marked {result.modified_count} interrupted trip(s) as failed")


def create_app(settings: Settings | None = None, providers: Providers | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http = httpx.AsyncClient(timeout=settings.http_timeout_seconds, limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))
        app.state.http = http
        app.state.providers = providers or build_providers(settings, http)
        app.state.jobs = JobRunner()
        db = await connect_mongo(settings.mongodb_uri, settings.mongodb_db)
        await recover_interrupted_trips(db)
        logger.info(f"🚀 {settings.app_name} v{settings.app_version} ready ({settings.environment}) — LLM: {app.state.providers.llm.name}")
        try:
            yield
        finally:
            await app.state.jobs.shutdown()
            await http.aclose()
            await close_mongo()
            logger.info("👋 Shutdown complete")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI travel planning, live search and booking API shared by the NomadIQ website and mobile app.",
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )
    app.state.settings = settings

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # bearer tokens, no cookies -> safe with explicit origins
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    for router in ROUTERS:
        app.include_router(router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"name": settings.app_name, "version": settings.app_version, "docs": f"{settings.api_prefix}/docs"}

    return app


def build_default_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level, log_to_file=not settings.is_test)
    return create_app(settings)
