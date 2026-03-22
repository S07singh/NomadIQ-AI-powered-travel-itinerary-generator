"""
FastAPI application setup for NomadIQ.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from datetime import datetime, timezone

from services.db_service import initialize_db
from api.routes import router as plan_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown logic."""
    logger.info("🚀 Starting NomadIQ API server")
    await initialize_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("👋 NomadIQ API server shutting down")


app = FastAPI(
    title="NomadIQ API",
    description="AI-powered travel planning API with multi-agent orchestration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": "NomadIQ API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include the plan routes
app.include_router(plan_router)
