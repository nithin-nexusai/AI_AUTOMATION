"""API dependencies for dependency injection."""

import logging
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, Request, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_redis(request: Request) -> redis.Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def verify_bolna_webhook(
    x_bolna_secret: str | None = Header(None, alias="X-Bolna-Secret"),
) -> bool:
    """Verify Bolna webhook requests using secret header.

    Bolna should send X-Bolna-Secret header with each webhook request.
    In development mode, authentication is skipped if no secret is configured.
    """
    # Skip auth in development if no secret configured
    if settings.is_development and not settings.bolna_webhook_secret:
        logger.warning("Bolna webhook auth skipped - no secret configured (dev mode)")
        return True

    if not settings.bolna_webhook_secret:
        logger.error("BOLNA_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook authentication not configured")

    if not x_bolna_secret:
        logger.warning("Bolna webhook request missing X-Bolna-Secret header")
        raise HTTPException(status_code=401, detail="Missing authentication header")

    if x_bolna_secret != settings.bolna_webhook_secret:
        logger.warning("Bolna webhook request with invalid secret")
        raise HTTPException(status_code=401, detail="Invalid authentication")

    return True


async def verify_admin_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> bool:
    """Verify admin API requests using API key header.

    Dashboard should send X-API-Key header with each request.
    In development mode, authentication is skipped if no key is configured.
    """
    # Skip auth in development if no key configured
    if settings.is_development and not settings.admin_api_key:
        logger.warning("Admin API auth skipped - no key configured (dev mode)")
        return True

    if not settings.admin_api_key:
        logger.error("ADMIN_API_KEY not configured")
        raise HTTPException(status_code=500, detail="API authentication not configured")

    if not x_api_key:
        logger.warning("Admin API request missing X-API-Key header")
        raise HTTPException(status_code=401, detail="Missing API key")

    if x_api_key != settings.admin_api_key:
        logger.warning("Admin API request with invalid API key")
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


# =============================================================================
# Type Aliases
# =============================================================================

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]
BolnaAuth = Annotated[bool, Depends(verify_bolna_webhook)]
AdminAuth = Annotated[bool, Depends(verify_admin_api_key)]
