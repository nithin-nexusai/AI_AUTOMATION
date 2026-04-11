"""CHICX Backend Webhooks.

These endpoints are called BY the CHICX backend to trigger notifications:
- OTP for login
- Order status updates
- Order confirmation calls

Marketing (cart reminders, product announcements, sales) is handled via AiSensy dashboard.
"""

import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.services.whatsapp import WhatsAppService
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/chicx", tags=["CHICX Notifications"])


# =============================================================================
# Pydantic Models
# =============================================================================


class SendOTPPayload(BaseModel):
    """Payload for sending login OTP via WhatsApp."""

    phone: str
    otp: str


class OrderUpdatePayload(BaseModel):
    """Payload for order status update notification."""
    
    phone: str
    order_id: str
    order_status: str
    tracking_url: str | None = None
    delivery_date: str | None = None


class OrderConfirmItem(BaseModel):
    """Item in order confirmation."""
    
    name: str
    qty: int = 1
    price: float | None = None


class OrderConfirmPayload(BaseModel):
    """Payload for order confirmation call."""
    
    phone: str
    order_id: str
    customer_name: str | None = None
    items: list[OrderConfirmItem] = []
    total_amount: float
    cod: bool = False  # Cash on delivery - typically needs confirmation
    delivery_address: str | None = None


# =============================================================================
# Webhook Authentication
# =============================================================================


def verify_chicx_webhook(
    x_chicx_secret: str = Header(None, alias="X-CHICX-Secret"),
) -> bool:
    """Verify CHICX webhook secret."""
    settings = get_settings()
    
    if not settings.chicx_api_key:
        logger.warning("CHICX_API_KEY not configured, skipping webhook auth")
        return True
    
    if x_chicx_secret != settings.chicx_api_key:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    return True


async def get_redis(request: Request) -> aioredis.Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


# =============================================================================
# Webhook Endpoints
# =============================================================================


@router.post("/send-otp")
async def handle_send_otp(
    payload: SendOTPPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    _auth: bool = Depends(verify_chicx_webhook),
) -> dict[str, Any]:
    """Send login OTP to user via WhatsApp.

    Called by CHICX backend when user logs in with OTP.

    Example request:
    ```json
    {
        "phone": "9876543210",
        "otp": "123456"
    }
    ```
    """
    logger.info(f"Send OTP webhook: phone={payload.phone}")

    phone = normalize_phone(payload.phone)

    # Build template components for authentication template
    # Meta authentication templates use: {{1}} = OTP code in body
    # Button must be "copy_code" type for OTP auto-copy functionality
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": payload.otp},
            ],
        },
        # Copy code button (Meta authentication template format)
        {
            "type": "button",
            "sub_type": "copy_code",
            "index": "0",
            "parameters": [
                {"type": "text", "text": payload.otp},
            ],
        },
    ]

    try:
        wa_service = WhatsAppService(db=db, redis_client=redis_client)

        result = await wa_service.send_template_message(
            to=phone,
            template_name="otp_login",
            language_code="en",
            components=components,
        )

        await wa_service.close()

        logger.info(f"Login OTP sent successfully to {phone}")

        return {
            "status": "ok",
            "message": f"OTP sent to {payload.phone}",
            "phone": payload.phone,
            "wa_message_id": result.get("messages", [{}])[0].get("id"),
        }

    except Exception as e:
        logger.error(f"Failed to send OTP to {payload.phone}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "phone": payload.phone,
        }


@router.post("/order-update")
async def handle_order_update(
    payload: OrderUpdatePayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    _auth: bool = Depends(verify_chicx_webhook),
) -> dict[str, Any]:
    """Handle order status update from CHICX backend.
    
    CHICX backend calls this when an order status changes.
    We send a WhatsApp notification to the customer.
    
    Template: order_update
    Parameters: {{1}} order_id, {{2}} order_status
    """
    logger.info(f"Order update webhook: {payload.order_id} -> {payload.order_status}")

    phone = normalize_phone(payload.phone)

    try:
        wa_service = WhatsAppService(db=db, redis_client=redis_client)
        
        # Build template components
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": payload.order_id},
                    {"type": "text", "text": payload.order_status},
                ],
            }
        ]
        
        # Add tracking URL button if provided
        # NOTE: Pass URL suffix if template has base URL, or full URL if fully dynamic
        if payload.tracking_url:
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {"type": "text", "text": payload.tracking_url}
                ],
            })

        result = await wa_service.send_template_message(
            to=phone,
            template_name="order_update",
            language_code="en",
            components=components,
        )
        
        await wa_service.close()
        
        logger.info(f"Order update sent to {phone}")
        
        return {
            "status": "ok",
            "message": f"Order update notification sent to {payload.phone}",
            "order_id": payload.order_id,
            "order_status": payload.order_status,
            "wa_message_id": result.get("messages", [{}])[0].get("id"),
        }
    
    except Exception as e:
        logger.error(f"Failed to send order update: {e}")
        return {
            "status": "error",
            "message": str(e),
            "order_id": payload.order_id,
        }


@router.post("/confirm-order")
async def handle_confirm_order(
    payload: OrderConfirmPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    _auth: bool = Depends(verify_chicx_webhook),
) -> dict[str, Any]:
    """Trigger outbound call to confirm order with customer.
    
    CHICX backend calls this for COD orders or high-value orders
    that need customer confirmation via phone call.
    
    Example request:
    ```json
    {
        "phone": "9876543210",
        "order_id": "ORD123456",
        "customer_name": "Rahul",
        "items": [{"name": "Blue Saree", "qty": 1, "price": 2499}],
        "total_amount": 2499.00,
        "cod": true
    }
    ```
    """
    from app.services.bolna import get_bolna_client, BolnaAPIError
    
    logger.info(f"Order confirmation webhook for: {payload.order_id}, phone: {payload.phone}")
    
    settings = get_settings()
    
    # Check if Bolna agent is configured
    if not settings.bolna_api_key:
        logger.error("BOLNA_API_KEY not configured")
        return {
            "status": "error",
            "message": "Bolna not configured",
            "order_id": payload.order_id,
        }
    
    # Check if confirmation agent ID is configured
    if not settings.bolna_confirmation_agent_id:
        logger.error("BOLNA_CONFIRMATION_AGENT_ID not configured")
        return {
            "status": "error",
            "message": "Confirmation agent not configured",
            "order_id": payload.order_id,
        }
    
    phone = normalize_phone(payload.phone)
    
    # Build items summary for voice
    items_summary = ", ".join([
        f"{item.qty} {item.name}" for item in payload.items
    ]) or "your items"
    
    # Context for the Bolna agent conversation
    context = {
        "order_id": payload.order_id,
        "customer_name": payload.customer_name or "customer",
        "items_summary": items_summary,
        "total_amount": payload.total_amount,
        "cod": payload.cod,
        "delivery_address": payload.delivery_address or "",
        "callback_order_id": payload.order_id,  # Used in call-complete to identify
    }
    
    # Store pending confirmation in Redis for tracking
    confirmation_key = f"pending_confirmation:{payload.order_id}"
    await redis_client.setex(
        confirmation_key,
        3600,  # 1 hour TTL
        payload.model_dump_json(),
    )
    
    try:
        bolna = get_bolna_client()
        
        result = await bolna.make_outbound_call(
            phone=phone,
            agent_id=settings.bolna_confirmation_agent_id,
            context=context,
        )
        
        call_id = result.get("call_id")
        logger.info(f"Outbound call initiated for order {payload.order_id}: {call_id}")
        
        # Store call_id -> order_id mapping in Redis for O(1) lookup
        # when call-complete webhook arrives
        if call_id:
            await redis_client.setex(
                f"confirmation_call:{call_id}",
                3600,  # 1 hour TTL (same as pending_confirmation)
                payload.order_id,
            )
        
        return {
            "status": "ok",
            "message": f"Confirmation call initiated for order {payload.order_id}",
            "order_id": payload.order_id,
            "call_id": call_id,
            "phone": payload.phone,
        }
        
    except BolnaAPIError as e:
        logger.error(f"Failed to initiate confirmation call: {e}")
        return {
            "status": "error",
            "message": str(e),
            "order_id": payload.order_id,
        }
    except Exception as e:
        logger.error(f"Error initiating confirmation call: {e}")
        return {
            "status": "error",
            "message": str(e),
            "order_id": payload.order_id,
        }

