"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession, RedisClient

router = APIRouter()


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str
    timestamp: str


class ServiceHealth(BaseModel):
    """Individual service health status."""

    status: str
    latency_ms: float | None = None
    error: str | None = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with service statuses."""

    status: str
    timestamp: str
    services: dict[str, ServiceHealth]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db: DbSession,
    redis_client: RedisClient,
) -> DetailedHealthResponse:
    """Detailed health check with database and Redis status."""
    services: dict[str, ServiceHealth] = {}

    # Check PostgreSQL
    try:
        start = datetime.now(timezone.utc)
        await db.execute(text("SELECT 1"))
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        services["database"] = ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        services["database"] = ServiceHealth(status="unhealthy", error=str(e))

    # Check Redis
    try:
        start = datetime.now(timezone.utc)
        await redis_client.ping()
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        services["redis"] = ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        services["redis"] = ServiceHealth(status="unhealthy", error=str(e))

    # Overall status
    all_healthy = all(s.status == "healthy" for s in services.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
    )
