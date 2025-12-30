"""Stats API endpoints for CHICX.

Exposes raw data APIs for backend team to build upon:
1. Total conversations
2. Orders tracked
3. Inbound calls
4. Messages per day
5. Conversation list
6. Call log table
7. Call status
8. Audio record
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import AdminAuth
from app.models.user import User
from app.models.conversation import Conversation, Message, ConversationStatus
from app.models.voice import Call, CallStatus
from app.models.system import AnalyticsEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["Stats"])


# =============================================================================
# Overview Stats
# =============================================================================


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> dict[str, Any]:
    """Get overview stats.

    Returns:
    - total_conversations: Total conversations today
    - orders_tracked: Orders tracked today
    - inbound_calls: Total inbound calls today
    - messages_today: Total messages today
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Total conversations today
    total_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.started_at >= today_start
        )
    ) or 0

    # Orders tracked (get_order_status tool calls)
    orders_tracked = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_type == "tool_call",
                AnalyticsEvent.created_at >= today_start,
                AnalyticsEvent.event_data["tool_name"].astext == "get_order_status",
            )
        )
    ) or 0

    # Inbound calls today
    inbound_calls = await db.scalar(
        select(func.count(Call.id)).where(Call.started_at >= today_start)
    ) or 0

    # Messages today
    messages_today = await db.scalar(
        select(func.count(Message.id)).where(Message.created_at >= today_start)
    ) or 0

    return {
        "total_conversations": total_conversations,
        "orders_tracked": orders_tracked,
        "inbound_calls": inbound_calls,
        "messages_today": messages_today,
    }


# =============================================================================
# Messages Per Day
# =============================================================================


@router.get("/messages-per-day")
async def get_messages_per_day(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
    days: int = Query(default=30, ge=1, le=90, description="Number of days"),
) -> dict[str, Any]:
    """Get message count per day.

    Returns list of {date, count} for the last N days.
    """
    data = []
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for i in range(days - 1, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        count = await db.scalar(
            select(func.count(Message.id)).where(
                and_(
                    Message.created_at >= day_start,
                    Message.created_at < day_end,
                )
            )
        ) or 0

        data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count,
        })

    return {"data": data}


# =============================================================================
# Conversations
# =============================================================================


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
    status: str | None = Query(default=None, description="Filter by status"),
    search: str | None = Query(default=None, description="Search by phone"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """List conversations with pagination."""
    offset = (page - 1) * limit

    query = select(Conversation).join(User)

    if status:
        try:
            status_enum = ConversationStatus(status)
            query = query.where(Conversation.status == status_enum)
        except ValueError:
            pass

    if search:
        query = query.where(User.phone.ilike(f"%{search}%"))

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginated results
    query = query.order_by(desc(Conversation.started_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        user = await db.get(User, conv.user_id)
        msg_count = await db.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        ) or 0

        items.append({
            "id": str(conv.id),
            "phone": user.phone if user else None,
            "status": conv.status.value,
            "channel": conv.channel.value,
            "message_count": msg_count,
            "started_at": conv.started_at.isoformat(),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


# =============================================================================
# Calls
# =============================================================================


@router.get("/calls")
async def list_calls(
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
    status: str | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """List calls with pagination (call log table)."""
    offset = (page - 1) * limit

    query = select(Call)

    if status:
        try:
            status_enum = CallStatus(status)
            query = query.where(Call.status == status_enum)
        except ValueError:
            pass

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginated results
    query = query.order_by(desc(Call.started_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    calls = result.scalars().all()

    items = []
    for call in calls:
        items.append({
            "id": str(call.id),
            "phone": call.phone,
            "status": call.status.value,
            "duration_seconds": call.duration_seconds,
            "language": call.language,
            "started_at": call.started_at.isoformat(),
            "has_recording": bool(call.recording_url),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/calls/{call_id}")
async def get_call_status(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> dict[str, Any]:
    """Get single call status."""
    try:
        call_uuid = UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call ID")

    call = await db.get(Call, call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return {
        "id": str(call.id),
        "phone": call.phone,
        "status": call.status.value,
        "duration_seconds": call.duration_seconds,
        "language": call.language,
        "started_at": call.started_at.isoformat(),
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "transcript": call.transcript.transcript if call.transcript else None,
        "has_recording": bool(call.recording_url),
    }


@router.get("/calls/{call_id}/audio")
async def get_call_audio(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: AdminAuth = None,
) -> dict[str, Any]:
    """Get audio recording URL for a call."""
    try:
        call_uuid = UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call ID")

    call = await db.get(Call, call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available")

    return {
        "call_id": str(call.id),
        "audio_url": call.recording_url,
        "duration_seconds": call.duration_seconds,
    }
