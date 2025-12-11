"""API dependencies for dependency injection."""

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


async def get_redis(request: Request) -> redis.Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]
