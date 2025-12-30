"""Analytics service for tracking events.

This module provides helpers to log analytics events like tool calls,
which are used by the Stats APIs for the dashboard.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import AnalyticsEvent

logger = logging.getLogger(__name__)


async def log_tool_call(
    db: AsyncSession,
    tool_name: str,
    arguments: dict[str, Any],
    result_success: bool = True,
    user_id: uuid.UUID | None = None,
    channel: str = "whatsapp",
) -> None:
    """Log a tool call event to analytics.

    Args:
        db: Database session
        tool_name: Name of the tool executed (e.g., "get_order_status")
        arguments: Arguments passed to the tool
        result_success: Whether the tool executed successfully
        user_id: Optional user ID if known
        channel: Channel where the tool was called ("whatsapp" or "voice")
    """
    try:
        event = AnalyticsEvent(
            user_id=user_id,
            event_type="tool_call",
            event_data={
                "tool_name": tool_name,
                "arguments": arguments,
                "success": result_success,
                "channel": channel,
            },
        )
        db.add(event)
        await db.flush()
        logger.debug(f"Logged tool call: {tool_name}")
    except Exception as e:
        # Don't fail the main operation if analytics logging fails
        logger.warning(f"Failed to log analytics event: {e}")


async def log_event(
    db: AsyncSession,
    event_type: str,
    event_data: dict[str, Any],
    user_id: uuid.UUID | None = None,
) -> None:
    """Log a generic analytics event.

    Args:
        db: Database session
        event_type: Type of event (e.g., "message_received", "call_completed")
        event_data: Additional event data
        user_id: Optional user ID
    """
    try:
        event = AnalyticsEvent(
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
        )
        db.add(event)
        await db.flush()
        logger.debug(f"Logged event: {event_type}")
    except Exception as e:
        logger.warning(f"Failed to log analytics event: {e}")
