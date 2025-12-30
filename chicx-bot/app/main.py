"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.api.admin import health, stats
from app.api.webhooks import whatsapp, bolna, chicx

settings = get_settings()

# Rate limiter - uses client IP address
limiter = Limiter(key_func=get_remote_address)


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

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://api.chicx.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(stats.router, tags=["Stats"])
app.include_router(whatsapp.router, tags=["WhatsApp"])
app.include_router(bolna.router, tags=["Voice"])  # Bolna handles all voice/telephony
app.include_router(chicx.router, tags=["CHICX Notifications"])  # CHICX backend notifications
