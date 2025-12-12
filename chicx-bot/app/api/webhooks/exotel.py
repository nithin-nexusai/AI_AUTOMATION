"""Exotel webhook for voice call updates.

Handles incoming webhooks from Exotel for:
- Call status updates (answered, completed, missed, failed)
- Recording availability notifications

Reference: https://developer.exotel.com/api/webhooks
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.models.voice import Call, CallStatus, CallDirection
from app.models.conversation import Conversation, ChannelType, ConversationStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/exotel", tags=["Exotel"])

settings = get_settings()


# Exotel status mapping to our CallStatus enum
EXOTEL_STATUS_MAP = {
    "completed": CallStatus.RESOLVED,
    "busy": CallStatus.MISSED,
    "no-answer": CallStatus.MISSED,
    "failed": CallStatus.FAILED,
    "canceled": CallStatus.MISSED,
}


def verify_exotel_signature(payload: bytes, signature: str) -> bool:
    """Verify Exotel webhook signature.

    Args:
        payload: Raw request body
        signature: X-Exotel-Signature header value

    Returns:
        True if signature is valid
    """
    if not settings.exotel_api_token:
        logger.warning("EXOTEL_API_TOKEN not configured, skipping signature verification")
        return True

    if not signature:
        logger.warning("No signature provided in webhook request")
        return False

    computed = hmac.new(
        key=settings.exotel_api_token.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check for Exotel webhook."""
    return {"status": "ok", "service": "exotel-webhook"}


@router.post("")
async def handle_exotel_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle incoming Exotel webhook.

    Exotel sends webhooks as form-urlencoded data with fields:
    - CallSid: Unique call identifier
    - From: Caller's phone number
    - To: Called number (your Exotel number)
    - Status: Call status (completed, busy, no-answer, failed, canceled)
    - Direction: inbound or outbound
    - RecordingUrl: URL to call recording (if available)
    - Duration: Call duration in seconds
    - StartTime: Call start time
    - EndTime: Call end time
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Exotel-Signature", "")

    if not verify_exotel_signature(body, signature):
        logger.warning("Invalid Exotel webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse form data
    form_data = await request.form()
    data = dict(form_data)

    logger.info(f"Exotel webhook received: {data}")

    call_sid = data.get("CallSid")
    if not call_sid:
        logger.warning("No CallSid in webhook payload")
        return {"status": "ignored", "reason": "no_call_sid"}

    # Extract call data
    from_number = normalize_phone(data.get("From", ""))
    to_number = normalize_phone(data.get("To", ""))
    status_str = data.get("Status", "").lower()
    direction_str = data.get("Direction", "inbound").lower()
    recording_url = data.get("RecordingUrl")
    duration = parse_duration(data.get("Duration"))
    start_time = parse_datetime(data.get("StartTime"))
    end_time = parse_datetime(data.get("EndTime"))

    # Map Exotel status to our enum
    call_status = EXOTEL_STATUS_MAP.get(status_str, CallStatus.FAILED)

    # Check if this is an escalation (transferred to human)
    if data.get("DialWhomNumber") or data.get("legs"):
        # Call was transferred/bridged to another number
        call_status = CallStatus.ESCALATED

    # For inbound calls, the customer is "From"
    # For outbound calls, the customer is "To"
    customer_phone = from_number if direction_str == "inbound" else to_number
    direction = CallDirection.INBOUND if direction_str == "inbound" else CallDirection.OUTBOUND

    # Find or create the call record
    result = await db.execute(
        select(Call).where(Call.exotel_call_id == call_sid)
    )
    call = result.scalar_one_or_none()

    if call:
        # Update existing call
        call.status = call_status
        if recording_url:
            call.recording_url = recording_url
        if duration:
            call.duration_seconds = duration
        if end_time:
            call.ended_at = end_time

        logger.info(f"Updated call {call_sid}: status={call_status.value}")
    else:
        # Create new call record
        # First, get or create user
        user = await get_or_create_user(db, customer_phone)

        # Create conversation for this call
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.VOICE,
            status=ConversationStatus.ACTIVE if call_status == CallStatus.RESOLVED else ConversationStatus.CLOSED,
            started_at=start_time or datetime.now(timezone.utc),
            ended_at=end_time,
        )
        db.add(conversation)
        await db.flush()

        # Create call record
        call = Call(
            conversation_id=conversation.id,
            user_id=user.id,
            phone=customer_phone,
            exotel_call_id=call_sid,
            direction=direction,
            status=call_status,
            duration_seconds=duration,
            recording_url=recording_url,
            started_at=start_time or datetime.now(timezone.utc),
            ended_at=end_time,
        )
        db.add(call)

        logger.info(f"Created call {call_sid}: phone={customer_phone}, status={call_status.value}")

    await db.commit()

    return {"status": "ok", "call_sid": call_sid}


@router.post("/recording")
async def handle_recording_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle recording availability notification.

    Exotel may send a separate webhook when recording is ready.
    """
    body = await request.body()
    signature = request.headers.get("X-Exotel-Signature", "")

    if not verify_exotel_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    form_data = await request.form()
    data = dict(form_data)

    call_sid = data.get("CallSid")
    recording_url = data.get("RecordingUrl")

    if not call_sid or not recording_url:
        return {"status": "ignored", "reason": "missing_data"}

    # Update call with recording URL
    result = await db.execute(
        select(Call).where(Call.exotel_call_id == call_sid)
    )
    call = result.scalar_one_or_none()

    if call:
        call.recording_url = recording_url
        await db.commit()
        logger.info(f"Updated recording URL for call {call_sid}")
        return {"status": "ok", "call_sid": call_sid}

    logger.warning(f"Call not found for recording update: {call_sid}")
    return {"status": "ignored", "reason": "call_not_found"}


# =============================================================================
# Helper Functions
# =============================================================================


def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing + prefix."""
    if not phone:
        return ""
    return phone.lstrip("+").strip()


def parse_duration(duration_str: str | None) -> int | None:
    """Parse duration string to seconds."""
    if not duration_str:
        return None
    try:
        return int(duration_str)
    except (ValueError, TypeError):
        return None


def parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse datetime string from Exotel.

    Exotel typically sends timestamps in ISO format or Unix timestamp.
    """
    if not dt_str:
        return None

    try:
        # Try ISO format first
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        # Try Unix timestamp
        return datetime.fromtimestamp(int(dt_str), tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    return None


async def get_or_create_user(db: AsyncSession, phone: str) -> User:
    """Get existing user or create new one."""
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=phone)
        db.add(user)
        await db.flush()
        logger.info(f"Created new user for phone: {phone}")

    return user
