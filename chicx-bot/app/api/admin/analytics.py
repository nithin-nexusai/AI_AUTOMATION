"""Analytics and Dashboard API endpoints.

Provides metrics and analytics data for the CHICX dashboard including:
- Conversation metrics
- Order statistics
- User engagement
- Bot performance
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message, ChannelType
from app.models.order import Order, OrderStatus
from app.models.system import AnalyticsEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/analytics", tags=["Analytics"])


# =============================================================================
# Dashboard Overview
# =============================================================================


@router.get("/dashboard")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
) -> dict[str, Any]:
    """Get dashboard overview with key metrics.

    Returns summary statistics for the dashboard including:
    - Total users and new users
    - Conversation counts
    - Message counts
    - Order statistics
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # User metrics
    total_users = await db.scalar(select(func.count(User.id)))
    new_users = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= cutoff)
    )

    # Conversation metrics
    total_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.started_at >= cutoff)
    )
    whatsapp_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.started_at >= cutoff,
                Conversation.channel == ChannelType.WHATSAPP,
            )
        )
    )
    voice_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.started_at >= cutoff,
                Conversation.channel == ChannelType.VOICE,
            )
        )
    )

    # Message metrics
    total_messages = await db.scalar(
        select(func.count(Message.id)).where(Message.created_at >= cutoff)
    )

    # Order metrics
    total_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.placed_at >= cutoff)
    )
    delivered_orders = await db.scalar(
        select(func.count(Order.id)).where(
            and_(
                Order.placed_at >= cutoff,
                Order.status == OrderStatus.DELIVERED,
            )
        )
    )

    return {
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "users": {
            "total": total_users or 0,
            "new": new_users or 0,
        },
        "conversations": {
            "total": total_conversations or 0,
            "whatsapp": whatsapp_conversations or 0,
            "voice": voice_conversations or 0,
        },
        "messages": {
            "total": total_messages or 0,
        },
        "orders": {
            "total": total_orders or 0,
            "delivered": delivered_orders or 0,
        },
    }


# =============================================================================
# Conversation Analytics
# =============================================================================


@router.get("/conversations")
async def get_conversation_analytics(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> dict[str, Any]:
    """Get detailed conversation analytics.

    Returns:
    - Daily conversation counts
    - Channel breakdown
    - Average messages per conversation
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Daily breakdown
    daily_stats = []
    for i in range(days):
        day_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        count = await db.scalar(
            select(func.count(Conversation.id)).where(
                and_(
                    Conversation.started_at >= day_start,
                    Conversation.started_at < day_end,
                )
            )
        )
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count or 0,
        })

    # Channel breakdown
    whatsapp_count = await db.scalar(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.started_at >= cutoff,
                Conversation.channel == ChannelType.WHATSAPP,
            )
        )
    )
    voice_count = await db.scalar(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.started_at >= cutoff,
                Conversation.channel == ChannelType.VOICE,
            )
        )
    )

    # Average messages per conversation
    total_convos = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.started_at >= cutoff)
    )
    total_msgs = await db.scalar(
        select(func.count(Message.id)).where(Message.created_at >= cutoff)
    )
    avg_messages = (total_msgs / total_convos) if total_convos else 0

    return {
        "period_days": days,
        "daily": list(reversed(daily_stats)),
        "by_channel": {
            "whatsapp": whatsapp_count or 0,
            "voice": voice_count or 0,
        },
        "avg_messages_per_conversation": round(avg_messages, 2),
    }


# =============================================================================
# Order Analytics
# =============================================================================


@router.get("/orders")
async def get_order_analytics(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> dict[str, Any]:
    """Get order analytics.

    Returns:
    - Daily order counts
    - Status breakdown
    - Revenue metrics
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Daily breakdown
    daily_stats = []
    for i in range(days):
        day_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        count = await db.scalar(
            select(func.count(Order.id)).where(
                and_(
                    Order.placed_at >= day_start,
                    Order.placed_at < day_end,
                )
            )
        )
        revenue = await db.scalar(
            select(func.sum(Order.total_amount)).where(
                and_(
                    Order.placed_at >= day_start,
                    Order.placed_at < day_end,
                )
            )
        )
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count or 0,
            "revenue": float(revenue) if revenue else 0,
        })

    # Status breakdown
    status_counts = {}
    for status in OrderStatus:
        count = await db.scalar(
            select(func.count(Order.id)).where(
                and_(
                    Order.placed_at >= cutoff,
                    Order.status == status,
                )
            )
        )
        status_counts[status.value] = count or 0

    # Total revenue
    total_revenue = await db.scalar(
        select(func.sum(Order.total_amount)).where(Order.placed_at >= cutoff)
    )
    total_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.placed_at >= cutoff)
    )
    avg_order_value = (total_revenue / total_orders) if total_orders else 0

    return {
        "period_days": days,
        "daily": list(reversed(daily_stats)),
        "by_status": status_counts,
        "total_revenue": float(total_revenue) if total_revenue else 0,
        "total_orders": total_orders or 0,
        "avg_order_value": round(float(avg_order_value), 2) if avg_order_value else 0,
    }


# =============================================================================
# User Analytics
# =============================================================================


@router.get("/users")
async def get_user_analytics(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> dict[str, Any]:
    """Get user analytics.

    Returns:
    - Daily new user signups
    - Active users (users with conversations)
    - User retention metrics
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Daily new users
    daily_stats = []
    for i in range(days):
        day_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        count = await db.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.created_at >= day_start,
                    User.created_at < day_end,
                )
            )
        )
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "new_users": count or 0,
        })

    # Total and new users
    total_users = await db.scalar(select(func.count(User.id)))
    new_users = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= cutoff)
    )

    # Active users (with conversations in period)
    active_users = await db.scalar(
        select(func.count(func.distinct(Conversation.user_id))).where(
            Conversation.started_at >= cutoff
        )
    )

    # Users with orders
    users_with_orders = await db.scalar(
        select(func.count(func.distinct(Order.user_id))).where(
            Order.placed_at >= cutoff
        )
    )

    return {
        "period_days": days,
        "daily": list(reversed(daily_stats)),
        "total_users": total_users or 0,
        "new_users": new_users or 0,
        "active_users": active_users or 0,
        "users_with_orders": users_with_orders or 0,
    }


# =============================================================================
# Bot Performance Analytics
# =============================================================================


@router.get("/bot-performance")
async def get_bot_performance(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> dict[str, Any]:
    """Get bot performance metrics.

    Returns:
    - Response times (if tracked)
    - Tool usage statistics
    - Error rates
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get analytics events for tool usage
    tool_events = await db.execute(
        select(AnalyticsEvent.event_data)
        .where(
            and_(
                AnalyticsEvent.event_type == "tool_call",
                AnalyticsEvent.created_at >= cutoff,
            )
        )
        .limit(1000)
    )
    tool_data = tool_events.scalars().all()

    # Count tool usage
    tool_usage = {}
    for data in tool_data:
        if data and "tool_name" in data:
            tool_name = data["tool_name"]
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

    # Get error events
    error_count = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_type == "error",
                AnalyticsEvent.created_at >= cutoff,
            )
        )
    )

    # Total events for rate calculation
    total_events = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.created_at >= cutoff
        )
    )

    error_rate = (error_count / total_events * 100) if total_events else 0

    return {
        "period_days": days,
        "tool_usage": tool_usage,
        "error_count": error_count or 0,
        "total_events": total_events or 0,
        "error_rate_percent": round(error_rate, 2),
    }


# =============================================================================
# Event Tracking
# =============================================================================


@router.post("/events")
async def track_event(
    event_type: str,
    event_data: dict[str, Any] | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Track an analytics event.

    Used to record custom events for analytics tracking.
    """
    from uuid import UUID

    event = AnalyticsEvent(
        user_id=UUID(user_id) if user_id else None,
        event_type=event_type,
        event_data=event_data or {},
    )
    db.add(event)
    await db.commit()

    logger.info(f"Tracked event: {event_type}")
    return {"status": "ok", "event_id": str(event.id)}


# =============================================================================
# Recent Activity
# =============================================================================


@router.get("/recent-activity")
async def get_recent_activity(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Get recent activity feed for dashboard.

    Returns recent conversations, orders, and events.
    """
    # Recent conversations
    recent_convos = await db.execute(
        select(Conversation)
        .order_by(Conversation.started_at.desc())
        .limit(limit)
    )
    conversations = [
        {
            "id": str(c.id),
            "user_id": str(c.user_id),
            "channel": c.channel.value,
            "status": c.status.value,
            "started_at": c.started_at.isoformat(),
        }
        for c in recent_convos.scalars().all()
    ]

    # Recent orders
    recent_orders = await db.execute(
        select(Order)
        .order_by(Order.placed_at.desc())
        .limit(limit)
    )
    orders = [
        {
            "id": str(o.id),
            "chicx_order_id": o.chicx_order_id,
            "user_id": str(o.user_id),
            "status": o.status.value,
            "total_amount": float(o.total_amount),
            "placed_at": o.placed_at.isoformat(),
        }
        for o in recent_orders.scalars().all()
    ]

    return {
        "conversations": conversations,
        "orders": orders,
    }
