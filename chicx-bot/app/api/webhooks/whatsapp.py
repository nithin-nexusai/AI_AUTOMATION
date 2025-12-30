"""WhatsApp webhook endpoint for Meta Cloud API.

This module handles:
- GET: Webhook verification from Meta during setup
- POST: Receiving WhatsApp messages and status updates

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError

from app.api.deps import DbSession, RedisClient
from app.config import get_settings
from app.schemas.whatsapp import WhatsAppWebhookPayload
from app.services.whatsapp import WhatsAppService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])


# ============================================================================
# GET - Webhook Verification
# ============================================================================


@router.get("", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> str:
    """Verify the webhook with Meta.

    This endpoint is called by Meta during webhook setup to verify that
    the endpoint is valid and owned by us. Meta sends a GET request with:
    - hub.mode: Should be "subscribe"
    - hub.verify_token: Must match our WHATSAPP_VERIFY_TOKEN
    - hub.challenge: A random string we must echo back

    Args:
        hub_mode: Should be "subscribe"
        hub_verify_token: Token to verify (must match our config)
        hub_challenge: Challenge string to return

    Returns:
        The hub.challenge string if verification succeeds

    Raises:
        HTTPException: 403 if verification fails
    """
    settings = get_settings()

    logger.info(
        f"Webhook verification request: mode={hub_mode}, "
        f"token_provided={bool(hub_verify_token)}"
    )

    # Verify all required parameters are present
    if not hub_mode or not hub_verify_token or not hub_challenge:
        logger.warning("Missing required verification parameters")
        raise HTTPException(
            status_code=400,
            detail="Missing required verification parameters",
        )

    # Verify mode is subscribe
    if hub_mode != "subscribe":
        logger.warning(f"Invalid hub.mode: {hub_mode}")
        raise HTTPException(
            status_code=403,
            detail="Invalid verification mode",
        )

    # Verify token matches our configured token
    if hub_verify_token != settings.whatsapp_verify_token:
        logger.warning("Webhook verification token mismatch")
        raise HTTPException(
            status_code=403,
            detail="Verification token mismatch",
        )

    logger.info("Webhook verification successful")
    return hub_challenge


# ============================================================================
# POST - Receive Messages
# ============================================================================


@router.post("", status_code=200)
async def receive_webhook(
    request: Request,
    db: DbSession,
    redis_client: RedisClient,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Receive WhatsApp webhook events.

    This endpoint receives all webhook events from Meta, including:
    - Incoming messages (text, interactive, media, etc.)
    - Message status updates (sent, delivered, read, failed)

    The endpoint returns 200 OK immediately and processes messages
    asynchronously in the background to meet Meta's timeout requirements.

    Security:
    - Verifies X-Hub-Signature-256 header using WHATSAPP_APP_SECRET
    - Validates payload structure with Pydantic schemas

    Args:
        request: FastAPI request object
        db: Database session (injected)
        redis_client: Redis client (injected)
        x_hub_signature_256: HMAC SHA256 signature header

    Returns:
        Simple acknowledgment response

    Raises:
        HTTPException: 403 if signature verification fails
        HTTPException: 400 if payload is invalid
    """
    settings = get_settings()

    # Read raw body for signature verification
    raw_body = await request.body()

    # Verify signature in production
    if settings.whatsapp_app_secret:
        service = WhatsAppService(db=db, redis_client=redis_client)
        if not service.verify_webhook_signature(raw_body, x_hub_signature_256 or ""):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(
                status_code=403,
                detail="Invalid signature",
            )
        await service.close()

    # Parse payload
    try:
        payload_dict = await request.json()
        payload = WhatsAppWebhookPayload.model_validate(payload_dict)
    except ValidationError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payload: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to parse payload",
        )

    # Log webhook info
    message_count = len(payload.get_messages())
    status_count = len(payload.get_statuses())
    phone_number_id = payload.get_phone_number_id()

    logger.info(
        f"Webhook received: phone_number_id={phone_number_id}, "
        f"messages={message_count}, statuses={status_count}"
    )

    # Verify this is for our phone number
    if phone_number_id and phone_number_id != settings.whatsapp_phone_number_id:
        logger.warning(
            f"Webhook for different phone number: {phone_number_id} "
            f"(expected: {settings.whatsapp_phone_number_id})"
        )
        # Still return 200 to acknowledge receipt
        return {"status": "ignored"}

    # Process messages and statuses
    if message_count > 0 or status_count > 0:
        service = WhatsAppService(db=db, redis_client=redis_client)
        try:
            # Process messages
            for message in payload.get_messages():
                try:
                    await service.process_message(message)
                except Exception as e:
                    logger.exception(f"Error processing message {message.id}: {e}")

            # Process statuses (these are quick)
            for status in payload.get_statuses():
                try:
                    await service.process_status_update(status)
                except Exception as e:
                    logger.exception(f"Error processing status {status.id}: {e}")
        finally:
            await service.close()

    return {"status": "ok"}


# ============================================================================
# Health Check for Webhook
# ============================================================================


@router.get("/health")
async def webhook_health() -> dict[str, str]:
    """Health check endpoint for the webhook.

    Returns:
        Simple health status
    """
    return {"status": "healthy", "service": "whatsapp-webhook"}
