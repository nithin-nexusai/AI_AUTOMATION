"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.admin import health, analytics
from app.api.webhooks import whatsapp, chicx

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup: Initialize Redis connection pool
    app.state.redis = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    yield
    # Shutdown: Close Redis connection
    await app.state.redis.close()


app = FastAPI(
    title="CHICX AI Platform",
    description="WhatsApp Commerce Bot + Voice Agent for CHICX",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(analytics.router, tags=["Analytics"])
app.include_router(whatsapp.router, tags=["WhatsApp"])
app.include_router(chicx.router, tags=["CHICX Backend"])
