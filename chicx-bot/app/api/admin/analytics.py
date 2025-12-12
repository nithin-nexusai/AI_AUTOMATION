"""Dashboard API endpoints for CHICX Admin Dashboard.

Simplified dashboard with 4 screens:
1. Overview - Today's snapshot (4 cards + messages by hour chart)
2. Conversations - CRM view with chat history
3. Voice - Call log with audio playback
4. Catalog Gaps - No-results searches

No WebSocket, no Redis pub/sub. Data refreshes on page reload.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message, ConversationStatus, MessageRole
from app.models.voice import Call, CallStatus
from app.models.system import AnalyticsEvent, SearchLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


# =============================================================================
# Screen 1: Overview
# =============================================================================


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get dashboard overview - today's snapshot.

    Returns:
    - conversations_today: Total conversations started today
    - orders_tracked: Count of order tracking queries today
    - calls_received: Total inbound calls today
    - calls_missed: Missed calls today
    - messages_by_hour: Message volume by hour (for bar chart)
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Conversations today
    conversations_today = await db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.started_at >= today_start
        )
    )

    # Orders tracked (count of get_order_status tool calls)
    orders_tracked = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_type == "tool_call",
                AnalyticsEvent.created_at >= today_start,
                AnalyticsEvent.event_data["tool_name"].astext == "get_order_status",
            )
        )
    )

    # Calls received today
    calls_received = await db.scalar(
        select(func.count(Call.id)).where(Call.started_at >= today_start)
    )

    # Missed calls today
    calls_missed = await db.scalar(
        select(func.count(Call.id)).where(
            and_(
                Call.started_at >= today_start,
                Call.status == CallStatus.MISSED,
            )
        )
    )

    # Messages by hour (for bar chart)
    messages_by_hour = []
    for hour in range(24):
        hour_start = today_start + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)

        count = await db.scalar(
            select(func.count(Message.id)).where(
                and_(
                    Message.created_at >= hour_start,
                    Message.created_at < hour_end,
                )
            )
        )
        messages_by_hour.append({
            "hour": hour,
            "count": count or 0,
        })

    return {
        "conversations_today": conversations_today or 0,
        "orders_tracked": orders_tracked or 0,
        "calls_received": calls_received or 0,
        "calls_missed": calls_missed or 0,
        "messages_by_hour": messages_by_hour,
    }


# =============================================================================
# Screen 2: Conversations (CRM View)
# =============================================================================


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(default=None, description="Filter by status"),
    search: str | None = Query(default=None, description="Search by phone number"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """List conversations with pagination and filters.

    Returns paginated list for the Conversations table.
    """
    offset = (page - 1) * limit

    # Build base query
    query = select(Conversation).join(User)

    # Apply filters
    if status:
        try:
            status_enum = ConversationStatus(status)
            query = query.where(Conversation.status == status_enum)
        except ValueError:
            pass

    if search:
        query = query.where(User.phone.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.order_by(desc(Conversation.started_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    conversations = result.scalars().all()

    # Build response
    items = []
    for conv in conversations:
        # Get message count
        msg_count = await db.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )

        # Get last message timestamp
        last_msg = await db.scalar(
            select(func.max(Message.created_at)).where(Message.conversation_id == conv.id)
        )

        # Get user phone
        user = await db.get(User, conv.user_id)

        items.append({
            "id": str(conv.id),
            "phone": user.phone if user else "Unknown",
            "status": conv.status.value,
            "channel": conv.channel.value,
            "message_count": msg_count or 0,
            "started_at": conv.started_at.isoformat(),
            "last_message_at": last_msg.isoformat() if last_msg else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get chat history for a conversation (popup view).

    Returns all messages in WhatsApp-style format.
    """
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    # Get conversation
    conversation = await db.get(Conversation, conv_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get user
    user = await db.get(User, conversation.user_id)

    # Get all messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_uuid)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "id": str(conversation.id),
        "phone": user.phone if user else "Unknown",
        "status": conversation.status.value,
        "channel": conversation.channel.value,
        "started_at": conversation.started_at.isoformat(),
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }


# =============================================================================
# Screen 3: Voice Manager
# =============================================================================


@router.get("/calls")
async def list_calls(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """List voice calls with pagination.

    Returns paginated list for the Voice call log table.
    """
    offset = (page - 1) * limit

    # Build query
    query = select(Call)

    if status:
        try:
            status_enum = CallStatus(status)
            query = query.where(Call.status == status_enum)
        except ValueError:
            pass

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.order_by(desc(Call.started_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    calls = result.scalars().all()

    items = []
    for call in calls:
        # Format duration as mm:ss
        duration_str = None
        if call.duration_seconds:
            minutes = call.duration_seconds // 60
            seconds = call.duration_seconds % 60
            duration_str = f"{minutes}:{seconds:02d}"

        items.append({
            "id": str(call.id),
            "phone": call.phone,
            "status": call.status.value,
            "duration": duration_str,
            "language": call.language,
            "started_at": call.started_at.isoformat(),
            "has_recording": bool(call.recording_url),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/calls/{call_id}/audio")
async def get_call_audio(
    call_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get audio URL for a call (S3 pre-signed URL).

    Returns URL for HTML5 audio player.
    """
    try:
        call_uuid = UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call ID")

    call = await db.get(Call, call_uuid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available")

    # TODO: Generate S3 pre-signed URL if needed
    # For now, return the stored URL directly
    return {
        "call_id": str(call.id),
        "audio_url": call.recording_url,
        "duration": call.duration_seconds,
    }


# =============================================================================
# Screen 4: Catalog Gaps
# =============================================================================


@router.get("/catalog-gaps")
async def get_catalog_gaps(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Get 'no results' searches for catalog gap analysis.

    Returns aggregated searches that returned 0 results,
    sorted by frequency to identify missing products.
    """
    # Get searches with 0 results, grouped by query
    result = await db.execute(
        select(
            SearchLog.query,
            SearchLog.language,
            func.count(SearchLog.id).label("count"),
            func.max(SearchLog.created_at).label("last_searched"),
        )
        .where(SearchLog.results_count == 0)
        .group_by(SearchLog.query, SearchLog.language)
        .order_by(desc("count"))
        .limit(limit)
    )
    rows = result.all()

    gaps = [
        {
            "query": row.query,
            "language": row.language,
            "count": row.count,
            "last_searched": row.last_searched.isoformat() if row.last_searched else None,
        }
        for row in rows
    ]

    return {
        "gaps": gaps,
        "total": len(gaps),
    }


# =============================================================================
# Voice Usage / Billing
# =============================================================================


@router.get("/voice-usage")
async def get_voice_usage(
    db: AsyncSession = Depends(get_db),
    year: int | None = Query(default=None, description="Year (defaults to current)"),
    month: int | None = Query(default=None, ge=1, le=12, description="Month (defaults to current)"),
) -> dict[str, Any]:
    """Get voice usage metrics for billing.

    Returns:
    - total_calls: Number of calls in the period
    - total_seconds: Total duration in seconds
    - total_minutes: Total duration in minutes (rounded up)
    - calls_by_status: Breakdown by call status
    - daily_breakdown: Daily usage for the month
    """
    now = datetime.now(timezone.utc)
    target_year = year or now.year
    target_month = month or now.month

    # Get first and last day of the month
    month_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
    if target_month == 12:
        month_end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)

    # Total calls in period
    total_calls = await db.scalar(
        select(func.count(Call.id)).where(
            and_(
                Call.started_at >= month_start,
                Call.started_at < month_end,
            )
        )
    ) or 0

    # Total seconds (only completed calls with duration)
    total_seconds = await db.scalar(
        select(func.coalesce(func.sum(Call.duration_seconds), 0)).where(
            and_(
                Call.started_at >= month_start,
                Call.started_at < month_end,
                Call.duration_seconds.isnot(None),
            )
        )
    ) or 0

    # Round up to minutes for billing
    total_minutes = (total_seconds + 59) // 60 if total_seconds > 0 else 0

    # Calls by status
    status_result = await db.execute(
        select(
            Call.status,
            func.count(Call.id).label("count"),
            func.coalesce(func.sum(Call.duration_seconds), 0).label("duration"),
        )
        .where(
            and_(
                Call.started_at >= month_start,
                Call.started_at < month_end,
            )
        )
        .group_by(Call.status)
    )
    status_rows = status_result.all()

    calls_by_status = {
        row.status.value: {
            "count": row.count,
            "duration_seconds": row.duration or 0,
            "duration_minutes": ((row.duration or 0) + 59) // 60,
        }
        for row in status_rows
    }

    # Daily breakdown
    daily_breakdown = []
    current_day = month_start
    while current_day < month_end:
        next_day = current_day + timedelta(days=1)

        day_calls = await db.scalar(
            select(func.count(Call.id)).where(
                and_(
                    Call.started_at >= current_day,
                    Call.started_at < next_day,
                )
            )
        ) or 0

        day_seconds = await db.scalar(
            select(func.coalesce(func.sum(Call.duration_seconds), 0)).where(
                and_(
                    Call.started_at >= current_day,
                    Call.started_at < next_day,
                    Call.duration_seconds.isnot(None),
                )
            )
        ) or 0

        daily_breakdown.append({
            "date": current_day.strftime("%Y-%m-%d"),
            "calls": day_calls,
            "duration_seconds": day_seconds,
            "duration_minutes": (day_seconds + 59) // 60 if day_seconds > 0 else 0,
        })

        current_day = next_day

    return {
        "period": {
            "year": target_year,
            "month": target_month,
            "month_name": month_start.strftime("%B"),
        },
        "total_calls": total_calls,
        "total_seconds": total_seconds,
        "total_minutes": total_minutes,
        "calls_by_status": calls_by_status,
        "daily_breakdown": daily_breakdown,
    }


# =============================================================================
# Utility: Log Search (called by tool executor)
# =============================================================================


@router.post("/log-search")
async def log_search(
    query: str,
    results_count: int,
    language: str | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Log a product search for catalog gap analysis.

    Called by the tool executor after each product search.
    """
    search_log = SearchLog(
        query=query,
        language=language,
        results_count=results_count,
        user_id=UUID(user_id) if user_id else None,
    )
    db.add(search_log)
    await db.commit()

    return {"status": "ok", "id": str(search_log.id)}
