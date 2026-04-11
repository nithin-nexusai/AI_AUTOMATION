"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

import logging

from app.config import get_settings
from app.core.llm import shutdown_llm_client
from app.services.embedding import shutdown_embedding_client
from app.services.chicx_api import shutdown_chicx_client
from app.services.bolna import shutdown_bolna_client
from app.api.admin import health, stats, recordings
from app.api.webhooks import whatsapp, bolna, chicx

logger = logging.getLogger(__name__)

settings = get_settings()

# Rate limiter - uses client IP address
limiter = Limiter(key_func=get_remote_address)


async def _check_embeddings() -> None:
    """Check if FAQ embeddings exist and warn if missing."""
    from sqlalchemy import text
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM embeddings WHERE source_type = 'faq'"))
            count = result.scalar() or 0

            faq_result = await db.execute(text("SELECT COUNT(*) FROM faqs WHERE is_active = true"))
            faq_count = faq_result.scalar() or 0

            if faq_count > 0 and count == 0:
                logger.warning(
                    f"⚠️  No FAQ embeddings found! Semantic search will not work. "
                    f"Run: python scripts/generate_embeddings.py"
                )
            elif count < faq_count:
                logger.warning(
                    f"⚠️  Only {count}/{faq_count} FAQs have embeddings. "
                    f"Run: python scripts/generate_embeddings.py --force"
                )
            else:
                logger.info(f"✓ FAQ embeddings ready: {count} embeddings for {faq_count} FAQs")
    except Exception as e:
        logger.warning(f"Could not check embeddings: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup: Validate database connection
    logger.info("Validating database connection...")
    try:
        from app.db.session import async_session_maker
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise RuntimeError(f"Cannot connect to database: {e}")
    
    # Initialize Redis connection pool
    logger.info("Initializing Redis connection...")
    try:
        app.state.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test Redis connection
        await app.state.redis.ping()
        logger.info("✓ Redis connection successful")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        logger.warning("Application will run without Redis (no message deduplication)")
        app.state.redis = None

    # Check embeddings on startup
    await _check_embeddings()

    yield
    # Shutdown: Close connections
    await shutdown_llm_client()
    await shutdown_embedding_client()
    await shutdown_chicx_client()
    await shutdown_bolna_client()
    if app.state.redis is not None:
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ] if settings.is_development else ["https://api.chicx.in"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(stats.router, tags=["Stats"])
app.include_router(recordings.router, tags=["Recordings"])
app.include_router(whatsapp.router, tags=["WhatsApp"])
app.include_router(bolna.router, tags=["Voice"])  # Bolna handles all voice/telephony
app.include_router(chicx.router, tags=["CHICX Notifications"])  # CHICX backend notifications
