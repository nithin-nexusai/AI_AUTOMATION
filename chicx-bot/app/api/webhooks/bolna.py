"""Bolna webhook for voice agent integration.

Handles incoming webhooks from Bolna voice agent for:
- Transcription results
- Tool execution requests
- Call completion notifications

Reference: https://github.com/bolna-ai/bolna
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.voice import Call, CallTranscript
from app.models.conversation import Conversation, Message, MessageRole, MessageType, ConversationStatus
from app.services.chicx_api import get_chicx_client, ChicxAPIError
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/bolna", tags=["Bolna"])

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
    exotel_call_id: str | None = None
    transcript: str
    segments: list[TranscriptSegment] | None = None
    language: str | None = None


class ToolCallPayload(BaseModel):
    """Tool execution request from Bolna."""
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    user_phone: str | None = None


class CallCompletePayload(BaseModel):
    """Call completion notification from Bolna."""
    call_id: str
    exotel_call_id: str | None = None
    duration_seconds: int | None = None
    status: str  # "completed", "escalated", "failed"
    transcript: str | None = None
    language: str | None = None


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
) -> dict[str, str]:
    """Handle transcription result from Bolna.

    Called when a segment of transcription is ready during or after a call.
    """
    logger.info(f"Bolna transcript received: call_id={payload.call_id}")

    # Find the call by Bolna call_id or Exotel call_id
    call = await find_call(db, payload.call_id, payload.exotel_call_id)

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
) -> dict[str, Any]:
    """Handle tool execution request from Bolna.

    Bolna calls this endpoint when the LLM wants to use a tool.
    We execute the tool and return the result.
    """
    logger.info(f"Bolna tool call: {payload.tool_name} with args {payload.arguments}")

    try:
        if payload.tool_name == "search_products":
            result = await execute_search_products(payload.arguments)
        elif payload.tool_name == "get_order_status":
            result = await execute_get_order_status(payload.arguments)
        elif payload.tool_name == "get_order_history":
            result = await execute_get_order_history(payload.arguments, payload.user_phone)
        elif payload.tool_name == "search_faq":
            result = await execute_search_faq(db, payload.arguments)
        else:
            result = {"error": f"Unknown tool: {payload.tool_name}"}

        return {"status": "ok", "result": result}

    except Exception as e:
        logger.exception(f"Error executing tool {payload.tool_name}: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/call-complete")
async def handle_call_complete(
    payload: CallCompletePayload,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle call completion notification from Bolna.

    Called when the voice call ends.
    """
    logger.info(f"Bolna call complete: call_id={payload.call_id}, status={payload.status}")

    # Find the call
    call = await find_call(db, payload.call_id, payload.exotel_call_id)

    if not call:
        logger.warning(f"Call not found for completion: {payload.call_id}")
        return {"status": "ignored", "reason": "call_not_found"}

    # Update call status
    from app.models.voice import CallStatus

    status_map = {
        "completed": CallStatus.RESOLVED,
        "escalated": CallStatus.ESCALATED,
        "failed": CallStatus.FAILED,
    }
    call.status = status_map.get(payload.status, CallStatus.RESOLVED)

    if payload.duration_seconds:
        call.duration_seconds = payload.duration_seconds

    if payload.language:
        call.language = payload.language

    call.ended_at = datetime.now(timezone.utc)

    # Update conversation status
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

    await db.commit()

    logger.info(f"Call {call.id} marked as {call.status.value}")
    return {"status": "ok", "call_id": str(call.id)}


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


async def execute_get_order_status(args: dict[str, Any]) -> dict[str, Any]:
    """Execute order status lookup via CHICX API."""
    client = get_chicx_client()
    order_id = args.get("order_id", "")

    if not order_id:
        return {"message": "Please provide your order ID. You can find it in your confirmation email."}

    try:
        order = await client.get_order(order_id)

        if not order:
            return {"message": f"I couldn't find order {order_id}. Please check the order ID and try again."}

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


# =============================================================================
# Helper Functions
# =============================================================================


async def find_call(
    db: AsyncSession,
    bolna_call_id: str,
    exotel_call_id: str | None = None,
) -> Call | None:
    """Find a call by Bolna call_id or Exotel call_id."""
    # Try Bolna call_id first
    result = await db.execute(
        select(Call).where(Call.bolna_call_id == bolna_call_id)
    )
    call = result.scalar_one_or_none()
    if call:
        return call

    # Try Exotel ID if provided
    if exotel_call_id:
        result = await db.execute(
            select(Call).where(Call.exotel_call_id == exotel_call_id)
        )
        call = result.scalar_one_or_none()
        if call:
            # Update the call with bolna_call_id for future lookups
            call.bolna_call_id = bolna_call_id
            await db.flush()
            return call

    return None
