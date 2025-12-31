"""Bolna webhook for voice agent integration.

Handles incoming webhooks from Bolna managed platform for:
- Call completion notifications (creates call records, captures recording URL)
- Transcription results
- Tool execution requests (product search, order status, FAQ)

Bolna handles all telephony, voice AI, and call recording.
This is the sole source of truth for voice call data.

Reference: https://docs.bolna.dev
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.api.deps import BolnaAuth
from app.models.voice import Call, CallTranscript, CallStatus, CallDirection
from app.models.conversation import Conversation, ChannelType, ConversationStatus
from app.models.user import User
from app.services.chicx_api import get_chicx_client, ChicxAPIError
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/bolna", tags=["Voice"])

settings = get_settings()


# =============================================================================
# Request/Response Models
# =============================================================================


class TranscriptSegment(BaseModel):
    """A segment of the call transcript."""
    speaker: str  # "user" or "assistant"
    text: str
    start_time: float
    end_time: float


class TranscriptPayload(BaseModel):
    """Transcript webhook payload from Bolna."""
    call_id: str
    transcript: str
    segments: list[TranscriptSegment] | None = None
    language: str | None = None


class ToolCallPayload(BaseModel):
    """Tool execution request from Bolna."""
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    user_phone: str | None = None


class TelephonyData(BaseModel):
    """Telephony data from Bolna webhook."""
    recording_url: str | None = None
    from_number: str | None = None
    to_number: str | None = None
    call_duration: int | None = None
    provider: str | None = None  # e.g., "twilio", "plivo", "exotel"


class CallCompletePayload(BaseModel):
    """Call completion notification from Bolna.
    
    Bolna managed platform sends call data including telephony info.
    This is the primary source for all call data.
    """
    call_id: str
    agent_id: str | None = None
    status: str  # "completed", "escalated", "failed", "missed"
    duration_seconds: int | None = None
    transcript: str | None = None
    language: str | None = None
    # Recording URL can come at top level or nested in telephony_data
    recording_url: str | None = None
    # Telephony data from Bolna (contains recording_url, phone numbers, etc.)
    telephony_data: TelephonyData | None = None
    # Phone numbers (may be at top level depending on Bolna config)
    from_number: str | None = None
    to_number: str | None = None
    user_phone: str | None = None  # Alias for from_number


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check for Bolna webhook."""
    return {"status": "ok", "service": "bolna-webhook"}


@router.post("/transcript")
async def handle_transcript(
    payload: TranscriptPayload,
    db: AsyncSession = Depends(get_db),
    _auth: BolnaAuth = None,
) -> dict[str, str]:
    """Handle transcription result from Bolna.

    Called when a segment of transcription is ready during or after a call.
    """
    logger.info(f"Bolna transcript received: call_id={payload.call_id}")

    # Find the call by Bolna call_id
    call = await find_call(db, payload.call_id)

    if not call:
        logger.warning(f"Call not found: {payload.call_id}")
        return {"status": "ignored", "reason": "call_not_found"}

    # Check if transcript already exists
    result = await db.execute(
        select(CallTranscript).where(CallTranscript.call_id == call.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing transcript
        existing.transcript = payload.transcript
        if payload.segments:
            existing.segments = [s.model_dump() for s in payload.segments]
    else:
        # Create new transcript
        transcript = CallTranscript(
            call_id=call.id,
            transcript=payload.transcript,
            segments=[s.model_dump() for s in payload.segments] if payload.segments else None,
        )
        db.add(transcript)

    # Update call language if detected
    if payload.language and not call.language:
        call.language = payload.language

    await db.commit()

    logger.info(f"Saved transcript for call {call.id}")
    return {"status": "ok", "call_id": str(call.id)}


@router.post("/tool")
async def handle_tool_call(
    payload: ToolCallPayload,
    db: AsyncSession = Depends(get_db),
    _auth: BolnaAuth = None,
) -> dict[str, Any]:
    """Handle tool execution request from Bolna.

    Bolna calls this endpoint when the LLM wants to use a tool.
    We execute the tool and return the result.
    """
    from app.services.analytics import log_tool_call

    logger.info(f"Bolna tool call: {payload.tool_name} with args {payload.arguments}")

    result = None
    success = True

    try:
        if payload.tool_name == "search_products":
            result = await execute_search_products(payload.arguments)
        elif payload.tool_name == "get_order_status":
            result = await execute_get_order_status(payload.arguments, payload.user_phone)
        elif payload.tool_name == "get_order_history":
            result = await execute_get_order_history(payload.arguments, payload.user_phone)
        elif payload.tool_name == "search_faq":
            result = await execute_search_faq(db, payload.arguments)
        elif payload.tool_name == "track_shipment":
            result = await execute_track_shipment(payload.arguments)
        else:
            result = {"error": f"Unknown tool: {payload.tool_name}"}
            success = False

        # Log analytics event for tool call
        await log_tool_call(
            db=db,
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            result_success=success and "error" not in (result or {}),
            channel="voice",
        )
        await db.commit()

        return {"status": "ok", "result": result}

    except Exception as e:
        logger.exception(f"Error executing tool {payload.tool_name}: {e}")
        # Still log the failed tool call
        await log_tool_call(
            db=db,
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            result_success=False,
            channel="voice",
        )
        await db.commit()
        return {"status": "error", "error": str(e)}


@router.post("/call-complete")
async def handle_call_complete(
    payload: CallCompletePayload,
    db: AsyncSession = Depends(get_db),
    _auth: BolnaAuth = None,
) -> dict[str, str]:
    """Handle call completion notification from Bolna.

    This is the PRIMARY source for all call data when using Bolna managed platform.
    Creates new call records if they don't exist, and updates existing ones.
    """
    logger.info(f"Bolna call complete: call_id={payload.call_id}, status={payload.status}")

    # Extract phone number from various possible locations in payload
    phone = (
        payload.user_phone 
        or payload.from_number 
        or (payload.telephony_data.from_number if payload.telephony_data else None)
    )
    if phone:
        phone = normalize_phone(phone)

    # Extract recording URL from various possible locations
    recording_url = payload.recording_url
    if not recording_url and payload.telephony_data:
        recording_url = payload.telephony_data.recording_url

    # Extract duration from various possible locations
    duration = payload.duration_seconds
    if not duration and payload.telephony_data and payload.telephony_data.call_duration:
        duration = payload.telephony_data.call_duration

    # Map status to enum
    status_map = {
        "completed": CallStatus.RESOLVED,
        "resolved": CallStatus.RESOLVED,
        "escalated": CallStatus.ESCALATED,
        "transferred": CallStatus.ESCALATED,
        "failed": CallStatus.FAILED,
        "error": CallStatus.FAILED,
        "missed": CallStatus.MISSED,
        "no-answer": CallStatus.MISSED,
        "busy": CallStatus.MISSED,
    }
    call_status = status_map.get(payload.status.lower(), CallStatus.RESOLVED)

    # Find existing call by Bolna call_id
    call = await find_call(db, payload.call_id)

    if call:
        # Update existing call
        call.status = call_status
        if duration:
            call.duration_seconds = duration
        if payload.language:
            call.language = payload.language
        if recording_url:
            call.recording_url = recording_url
        call.ended_at = datetime.now(timezone.utc)
        
        logger.info(f"Updated existing call {call.id}")
    else:
        # CREATE NEW CALL - Bolna is the sole source of call data
        if not phone:
            logger.warning(f"Cannot create call without phone number: call_id={payload.call_id}")
            return {"status": "error", "reason": "missing_phone_number"}

        # Get or create user
        user = await get_or_create_user(db, phone)

        # Create conversation for this call
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.VOICE,
            status=ConversationStatus.CLOSED,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db.add(conversation)
        await db.flush()

        # Create new call record
        call = Call(
            conversation_id=conversation.id,
            user_id=user.id,
            phone=phone,
            bolna_call_id=payload.call_id,
            direction=CallDirection.INBOUND,  # Assume inbound for Bolna calls
            status=call_status,
            duration_seconds=duration,
            recording_url=recording_url,
            language=payload.language,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db.add(call)
        await db.flush()

        logger.info(f"Created new call {call.id} for phone {phone}")

    # Update conversation status if exists
    if call.conversation_id:
        conversation = await db.get(Conversation, call.conversation_id)
        if conversation:
            conversation.status = ConversationStatus.CLOSED
            conversation.ended_at = datetime.now(timezone.utc)

    # Save final transcript if provided
    if payload.transcript:
        result = await db.execute(
            select(CallTranscript).where(CallTranscript.call_id == call.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.transcript = payload.transcript
        else:
            transcript = CallTranscript(
                call_id=call.id,
                transcript=payload.transcript,
            )
            db.add(transcript)

    # =========================================================================
    # Check for Order Confirmation Calls
    # =========================================================================
    # If this was an outbound confirmation call, extract result and notify CHICX
    
    confirmation_result = await process_confirmation_call(
        call_id=payload.call_id,
        transcript=payload.transcript,
        status=payload.status,
    )
    
    if confirmation_result:
        logger.info(f"Confirmation call result: order={confirmation_result['order_id']}, confirmed={confirmation_result['confirmed']}")

    await db.commit()

    logger.info(f"Call {call.id} marked as {call.status.value}, recording_url={'set' if recording_url else 'not set'}")
    return {"status": "ok", "call_id": str(call.id), "recording_available": bool(recording_url)}


# =============================================================================
# Tool Execution Functions
# =============================================================================


async def execute_search_products(args: dict[str, Any]) -> dict[str, Any]:
    """Execute product search via CHICX API."""
    client = get_chicx_client()

    try:
        result = await client.search_products(
            query=args.get("query", ""),
            category=args.get("category"),
            limit=3,  # Fewer results for voice
        )

        # Simplify for voice output
        products = result.get("products", [])
        if not products:
            return {"message": "No products found matching your search."}

        # Format for speech
        summaries = []
        for p in products[:3]:
            name = p.get("name", "Product")
            price = p.get("price", 0)
            summaries.append(f"{name} at {price} rupees")

        return {
            "products": summaries,
            "message": f"I found {len(summaries)} products: " + ", ".join(summaries),
        }

    except ChicxAPIError as e:
        logger.error(f"Product search error: {e}")
        return {"message": "Sorry, I couldn't search products right now. Please try again."}


async def execute_get_order_status(args: dict[str, Any], user_phone: str | None) -> dict[str, Any]:
    """Execute order status lookup via CHICX API.
    
    Args:
        args: Tool arguments containing order_id
        user_phone: Caller's phone number for authorization
        
    Returns:
        Order status information if authorized, error message otherwise
    """
    from app.utils.phone import normalize_phone
    
    client = get_chicx_client()
    order_id = args.get("order_id", "")

    if not order_id:
        return {"message": "Please provide your order ID. You can find it in your confirmation email."}
    
    # Verify caller identity
    if not user_phone:
        logger.warning(f"Order status check without phone number: order_id={order_id}")
        return {"message": "Unable to verify your identity. Please try calling again."}

    try:
        order = await client.get_order(order_id)

        if not order:
            return {"message": f"I couldn't find order {order_id}. Please check the order ID and try again."}
        
        # Security check: Verify order belongs to caller
        order_phone = order.get("phone", "")
        normalized_caller = normalize_phone(user_phone)
        normalized_order = normalize_phone(order_phone)
        
        if normalized_caller != normalized_order:
            # Unauthorized access attempt
            logger.warning(
                f"Unauthorized order access attempt: "
                f"caller={user_phone} (normalized={normalized_caller}) "
                f"tried order={order_id} belonging to={order_phone} (normalized={normalized_order})"
            )
            return {"message": f"Order {order_id} not found in your account. Please check the order ID."}
        
        # Authorized - return order status
        status = order.get("status", "unknown")
        status_messages = {
            "placed": "Your order has been placed and is being processed.",
            "confirmed": "Your order is confirmed and will be shipped soon.",
            "shipped": "Great news! Your order has been shipped.",
            "out_for_delivery": "Your order is out for delivery today!",
            "delivered": "Your order has been delivered.",
            "cancelled": "This order has been cancelled.",
        }

        message = status_messages.get(status, f"Your order status is {status}.")

        if order.get("tracking_number"):
            message += f" Your tracking number is {order['tracking_number']}."

        return {"status": status, "message": message}

    except ChicxAPIError as e:
        logger.error(f"Order status error: {e}")
        return {"message": "Sorry, I couldn't check your order status right now. Please try again."}



async def execute_get_order_history(args: dict[str, Any], user_phone: str | None) -> dict[str, Any]:
    """Execute order history lookup via CHICX API."""
    if not user_phone:
        return {"message": "I need your phone number to look up your orders."}

    client = get_chicx_client()

    try:
        result = await client.get_order_by_phone(
            phone=user_phone,
            limit=3,
        )

        orders = result.get("orders", [])
        if not orders:
            return {"message": "I don't see any orders for your phone number."}

        # Format for speech
        summaries = []
        for o in orders[:3]:
            order_id = o.get("chicx_order_id", o.get("id", ""))
            status = o.get("status", "unknown")
            summaries.append(f"Order {order_id} is {status}")

        return {
            "orders": summaries,
            "message": f"You have {len(summaries)} recent orders: " + ". ".join(summaries),
        }

    except ChicxAPIError as e:
        logger.error(f"Order history error: {e}")
        return {"message": "Sorry, I couldn't get your order history right now. Please try again."}


async def execute_search_faq(db: AsyncSession, args: dict[str, Any]) -> dict[str, Any]:
    """Execute FAQ search using pgvector."""
    query = args.get("query", "")

    if not query:
        return {"message": "What would you like to know about?"}

    embedding_service = EmbeddingService(db)

    try:
        faqs = await embedding_service.search_faqs(
            query=query,
            limit=1,  # Just the best match for voice
        )

        if not faqs:
            return {
                "message": "I don't have specific information about that. "
                "For detailed help, please contact support at support@chicx.in."
            }

        # Return the best matching answer
        best_match = faqs[0]
        return {
            "answer": best_match["answer"],
            "message": best_match["answer"],
        }

    except Exception as e:
        logger.error(f"FAQ search error: {e}")
        return {"message": "Sorry, I couldn't find that information. Please contact support@chicx.in."}


async def execute_track_shipment(args: dict[str, Any]) -> dict[str, Any]:
    """Execute track_shipment tool via Shiprocket API."""
    from app.services.shiprocket import get_shiprocket_client, ShiprocketAPIError

    awb_number = args.get("awb_number", "")

    if not awb_number:
        return {"message": "I need the tracking number or AWB number to track your shipment."}

    logger.info(f"Tracking shipment for voice: AWB={awb_number}")

    try:
        shiprocket = get_shiprocket_client()
        result = await shiprocket.track_by_awb(awb_number)

        if not result.get("found"):
            return {
                "message": f"I couldn't find any shipment with tracking number {awb_number}. Please verify the number."
            }

        # Format response for voice
        status = result.get("current_status", "Unknown")
        location = result.get("current_location", "")
        edd = result.get("edd", "")
        courier = result.get("courier", "")

        voice_response = f"Your shipment is currently {status}"
        if location:
            voice_response += f" at {location}"
        if courier:
            voice_response += f" via {courier}"
        if edd:
            voice_response += f". Expected delivery is {edd}"

        return {
            "status": status,
            "location": location,
            "courier": courier,
            "expected_delivery": edd,
            "message": voice_response,
        }

    except ShiprocketAPIError as e:
        logger.error(f"Shiprocket API error: {e}")
        return {"message": "I'm unable to fetch tracking information right now. Please try again later."}
    except Exception as e:
        logger.error(f"Tracking error: {e}")
        return {"message": "Sorry, I couldn't track that shipment. Please try again."}


# =============================================================================
# Helper Functions
# =============================================================================


async def find_call(
    db: AsyncSession,
    bolna_call_id: str,
) -> Call | None:
    """Find a call by Bolna call_id."""
    result = await db.execute(
        select(Call).where(Call.bolna_call_id == bolna_call_id)
    )
    return result.scalar_one_or_none()


def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing + prefix and spaces."""
    if not phone:
        return ""
    return phone.lstrip("+").replace(" ", "").replace("-", "").strip()


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


# =============================================================================
# Order Confirmation Processing
# =============================================================================


async def process_confirmation_call(
    call_id: str,
    transcript: str | None,
    status: str,
) -> dict[str, Any] | None:
    """Process confirmation call result and notify CHICX backend.
    
    Checks if this was an outbound confirmation call by looking up in Redis.
    If found, extracts confirmation result from transcript and sends callback.
    
    Args:
        call_id: Bolna call ID
        transcript: Call transcript
        status: Call completion status
        
    Returns:
        Dict with confirmation result, or None if not a confirmation call
    """
    import redis.asyncio as aioredis
    from app.services.chicx_api import get_chicx_client
    
    # Get Redis client
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None
    
    try:
        # Look for pending confirmations matching this call
        # We stored the order_id when initiating the call
        # Check by scanning for pending_confirmation keys
        
        # For now, we'll extract order_id from transcript context if available
        # In production, you'd store call_id -> order_id mapping when making the call
        
        # Search for any pending confirmations
        keys = await redis_client.keys("pending_confirmation:*")
        
        if not keys:
            return None
        
        # Check each pending confirmation (in production, use a proper mapping)
        for key in keys:
            order_data = await redis_client.get(key)
            if not order_data:
                continue
            
            import json
            try:
                order_info = json.loads(order_data)
            except json.JSONDecodeError:
                continue
            
            order_id = order_info.get("order_id", "")
            
            # Determine if order was confirmed from transcript
            confirmed = False
            confirmation_notes = ""
            
            if status in ("missed", "no-answer", "busy", "failed"):
                # Call didn't connect
                confirmed = False
                confirmation_notes = f"Call not answered: {status}"
            elif transcript:
                # Analyze transcript for confirmation
                transcript_lower = transcript.lower()
                
                # Look for positive confirmations
                positive_keywords = ["yes", "confirm", "haan", "theek", "ok", "okay", "proceed", "correct", "sure"]
                negative_keywords = ["no", "cancel", "nahi", "wrong", "incorrect", "stop", "reject"]
                
                # Count keyword matches
                positive_count = sum(1 for kw in positive_keywords if kw in transcript_lower)
                negative_count = sum(1 for kw in negative_keywords if kw in transcript_lower)
                
                if positive_count > negative_count:
                    confirmed = True
                    confirmation_notes = "Customer confirmed order via voice call"
                elif negative_count > 0:
                    confirmed = False
                    confirmation_notes = "Customer rejected/cancelled order via voice call"
                else:
                    # Unclear - default to not confirmed
                    confirmed = False
                    confirmation_notes = "Customer response unclear"
            else:
                confirmation_notes = "No transcript available"
            
            # Send confirmation to CHICX backend
            try:
                chicx_client = get_chicx_client()
                await chicx_client.confirm_order(
                    order_id=order_id,
                    confirmed=confirmed,
                    confirmation_notes=confirmation_notes,
                )
                logger.info(f"Sent confirmation to CHICX: order={order_id}, confirmed={confirmed}")
            except Exception as e:
                logger.error(f"Failed to send confirmation to CHICX: {e}")
            
            # Delete the pending confirmation
            await redis_client.delete(key)
            
            return {
                "order_id": order_id,
                "confirmed": confirmed,
                "notes": confirmation_notes,
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing confirmation call: {e}")
        return None
    finally:
        await redis_client.close()

