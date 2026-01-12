"""CHICX Backend Webhooks.

These endpoints are called BY the CHICX backend to trigger notifications:
- Cart abandonment reminders
- New product announcements
- Order status updates

The CHICX backend calls these webhooks, and we send WhatsApp messages to customers.
"""

import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.services.whatsapp import WhatsAppService, WhatsAppChannel
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/chicx", tags=["CHICX Notifications"])


# =============================================================================
# Pydantic Models
# =============================================================================


class SendOTPPayload(BaseModel):
    """Payload for sending OTP via WhatsApp.

    Types:
    - forgot_password: User forgot password on website
    - purchase_verification: Verify purchase/checkout
    - login: Login verification
    """

    phone: str
    otp: str
    type: str = "login"  # forgot_password, purchase_verification, login
    customer_name: str | None = None
    order_id: str | None = None  # For purchase_verification


class CartReminderPayload(BaseModel):
    """Payload for cart abandonment reminder."""

    phone: str
    customer_name: str | None = None
    product_name: str
    cart_total: float | None = None
    checkout_url: str | None = None  # Dynamic URL suffix for template button


class NewProductPayload(BaseModel):
    """Payload for new product announcement with poster image."""

    phones: list[str]  # List of phone numbers to notify
    product_name: str
    product_price: float
    image_url: str  # Required: Poster/product image URL (must be publicly accessible HTTPS)
    product_url: str | None = None  # Optional: Dynamic URL suffix for template button

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        """Validate image URL is HTTPS (required by Meta)."""
        if not v.startswith("https://"):
            raise ValueError("image_url must be HTTPS (required by WhatsApp)")
        return v

    @field_validator("phones")
    @classmethod
    def validate_phones_limit(cls, v: list[str]) -> list[str]:
        """Limit broadcast size to prevent abuse."""
        if len(v) > 1000:
            raise ValueError("Maximum 1000 phones per request")
        if len(v) == 0:
            raise ValueError("At least one phone number required")
        return v


class SaleAnnouncementPayload(BaseModel):
    """Payload for sale/promotion announcement with poster image."""

    phones: list[str]  # List of phone numbers to notify
    sale_title: str  # e.g., "Diwali Sale", "End of Season Sale"
    discount_text: str  # e.g., "Up to 50% OFF", "Flat 30% OFF"
    image_url: str  # Required: Sale poster image URL (must be publicly accessible HTTPS)
    sale_url: str | None = None  # Optional: Dynamic URL suffix for template button
    valid_till: str | None = None  # Optional: e.g., "31st December"

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        """Validate image URL is HTTPS (required by Meta)."""
        if not v.startswith("https://"):
            raise ValueError("image_url must be HTTPS (required by WhatsApp)")
        return v

    @field_validator("phones")
    @classmethod
    def validate_phones_limit(cls, v: list[str]) -> list[str]:
        """Limit broadcast size to prevent abuse."""
        if len(v) > 1000:
            raise ValueError("Maximum 1000 phones per request")
        if len(v) == 0:
            raise ValueError("At least one phone number required")
        return v


class OrderUpdatePayload(BaseModel):
    """Payload for order status update notification."""
    
    phone: str
    order_id: str
    order_status: str
    tracking_url: str | None = None
    delivery_date: str | None = None


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
    """Send OTP to user via WhatsApp.

    Called by CHICX backend when:
    - User requests password reset (forgot_password)
    - User makes a purchase and needs verification (purchase_verification)
    - User logs in with OTP (login)

    Example request:
    ```json
    {
        "phone": "9876543210",
        "otp": "123456",
        "type": "forgot_password",
        "customer_name": "Priya"
    }
    ```

    For purchase verification:
    ```json
    {
        "phone": "9876543210",
        "otp": "123456",
        "type": "purchase_verification",
        "customer_name": "Priya",
        "order_id": "ORD123456"
    }
    ```
    """
    logger.info(f"Send OTP webhook: type={payload.type}, phone={payload.phone}")

    phone = normalize_phone(payload.phone)

    # Map OTP type to template name
    template_map = {
        "login": "otp_login",
        "forgot_password": "otp_password_reset",
        "purchase_verification": "otp_purchase",
    }
    template_name = template_map.get(payload.type, "otp_login")

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
        # Use PRIMARY channel for OTP (authentication messages)
        wa_service = WhatsAppService(db=db, redis_client=redis_client, channel=WhatsAppChannel.PRIMARY)

        result = await wa_service.send_template_message(
            to=phone,
            template_name=template_name,
            language_code="en",
            components=components,
        )

        await wa_service.close()

        logger.info(f"OTP sent successfully to {phone} (type: {payload.type}, template: {template_name})")

        return {
            "status": "ok",
            "message": f"OTP sent to {payload.phone}",
            "phone": payload.phone,
            "type": payload.type,
            "template": template_name,
            "wa_message_id": result.get("messages", [{}])[0].get("id"),
        }

    except Exception as e:
        logger.error(f"Failed to send OTP to {payload.phone}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "phone": payload.phone,
            "type": payload.type,
        }


@router.post("/cart-reminder")
async def handle_cart_reminder(
    payload: CartReminderPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    _auth: bool = Depends(verify_chicx_webhook),
) -> dict[str, Any]:
    """Handle cart abandonment reminder from CHICX backend.
    
    CHICX backend calls this when a customer abandons their cart.
    We send a WhatsApp reminder message.
    
    Template: cart_reminder
    Parameters: {{1}} customer_name, {{2}} product_name, {{3}} cart_total
    """
    logger.info(f"Cart reminder webhook for phone: {payload.phone}, product: {payload.product_name}")

    phone = normalize_phone(payload.phone)

    try:
        # Use MARKETING channel for cart reminders
        wa_service = WhatsAppService(db=db, redis_client=redis_client, channel=WhatsAppChannel.MARKETING)
        
        # Build template components
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": payload.customer_name or "there"},
                    {"type": "text", "text": payload.product_name},
                    {"type": "text", "text": f"₹{payload.cart_total:.0f}" if payload.cart_total else "your cart"},
                ],
            }
        ]
        
        # Add button with checkout URL if provided
        # NOTE: If template URL is "https://chicx.in/checkout/{{1}}", pass only the suffix
        # If template URL is fully dynamic "{{1}}", pass the full URL
        if payload.checkout_url:
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {"type": "text", "text": payload.checkout_url}
                ],
            })
        
        # Send template message
        result = await wa_service.send_template_message(
            to=phone,
            template_name="cart_reminder",
            language_code="en",
            components=components,
        )
        
        await wa_service.close()
        
        logger.info(f"Cart reminder sent to {phone}")
        
        return {
            "status": "ok",
            "message": f"Cart reminder sent to {payload.phone}",
            "phone": payload.phone,
            "wa_message_id": result.get("messages", [{}])[0].get("id"),
        }
    
    except Exception as e:
        logger.error(f"Failed to send cart reminder: {e}")
        return {
            "status": "error",
            "message": str(e),
            "phone": payload.phone,
        }


@router.post("/new-product")
async def handle_new_product(
    payload: NewProductPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    _auth: bool = Depends(verify_chicx_webhook),
) -> dict[str, Any]:
    """Handle new product announcement from CHICX backend.

    CHICX backend calls this when a new product is added.
    We send WhatsApp broadcast messages with poster image to all specified phones.

    Template: new_product (with image header)
    Header: Image (poster/product image)
    Body: {{1}} product_name, {{2}} product_price
    Button: Shop Now -> product_url
    """
    logger.info(f"New product webhook for {len(payload.phones)} phones: {payload.product_name}")

    # Use MARKETING channel for new product announcements
    wa_service = WhatsAppService(db=db, redis_client=redis_client, channel=WhatsAppChannel.MARKETING)

    sent_count = 0
    failed_count = 0

    for phone in payload.phones:
        try:
            normalized_phone = normalize_phone(phone)

            # Build template components with image header
            components = [
                # Image header (poster)
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "image",
                            "image": {"link": payload.image_url},
                        }
                    ],
                },
                # Body text
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": payload.product_name},
                        {"type": "text", "text": f"₹{payload.product_price:.0f}"},
                    ],
                },
            ]

            # Add button with product URL if provided
            # NOTE: Pass URL suffix if template has base URL, or full URL if fully dynamic
            if payload.product_url:
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {"type": "text", "text": payload.product_url}
                    ],
                })

            await wa_service.send_template_message(
                to=normalized_phone,
                template_name="new_product",
                language_code="en",
                components=components,
            )

            sent_count += 1

        except Exception as e:
            logger.error(f"Failed to send new product notification to {phone}: {e}")
            failed_count += 1

    await wa_service.close()

    return {
        "status": "ok",
        "message": "New product broadcast completed",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total": len(payload.phones),
    }


@router.post("/sale-announcement")
async def handle_sale_announcement(
    payload: SaleAnnouncementPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    _auth: bool = Depends(verify_chicx_webhook),
) -> dict[str, Any]:
    """Handle sale/promotion announcement from CHICX backend.

    CHICX backend calls this to announce sales and promotions.
    We send WhatsApp broadcast messages with sale poster to all specified phones.

    Template: sale_announcement (with image header)
    Header: Image (sale poster)
    Body: {{1}} sale_title, {{2}} discount_text, {{3}} valid_till (optional)
    Button: Shop Now -> sale_url
    """
    logger.info(f"Sale announcement webhook for {len(payload.phones)} phones: {payload.sale_title}")

    # Use MARKETING channel for sale announcements
    wa_service = WhatsAppService(db=db, redis_client=redis_client, channel=WhatsAppChannel.MARKETING)

    sent_count = 0
    failed_count = 0

    for phone in payload.phones:
        try:
            normalized_phone = normalize_phone(phone)

            # Build template components with image header
            components = [
                # Image header (sale poster)
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "image",
                            "image": {"link": payload.image_url},
                        }
                    ],
                },
                # Body text
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": payload.sale_title},
                        {"type": "text", "text": payload.discount_text},
                        {"type": "text", "text": payload.valid_till or "limited time"},
                    ],
                },
            ]

            # Add button with sale URL if provided
            # NOTE: Pass URL suffix if template has base URL, or full URL if fully dynamic
            if payload.sale_url:
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {"type": "text", "text": payload.sale_url}
                    ],
                })

            await wa_service.send_template_message(
                to=normalized_phone,
                template_name="sale_announcement",
                language_code="en",
                components=components,
            )

            sent_count += 1

        except Exception as e:
            logger.error(f"Failed to send sale announcement to {phone}: {e}")
            failed_count += 1

    await wa_service.close()

    return {
        "status": "ok",
        "message": "Sale announcement broadcast completed",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total": len(payload.phones),
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
        # Use PRIMARY channel for order updates (utility/transactional)
        wa_service = WhatsAppService(db=db, redis_client=redis_client, channel=WhatsAppChannel.PRIMARY)
        
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


# =============================================================================
# Order Confirmation (Outbound Call)
# =============================================================================


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
        
        # Get agent ID from settings (you'll need to add this)
        agent_id = getattr(settings, 'bolna_confirmation_agent_id', '') or settings.bolna_api_key[:20]
        
        result = await bolna.make_outbound_call(
            phone=phone,
            agent_id=agent_id,
            context=context,
        )
        
        logger.info(f"Outbound call initiated for order {payload.order_id}: {result.get('call_id')}")
        
        return {
            "status": "ok",
            "message": f"Confirmation call initiated for order {payload.order_id}",
            "order_id": payload.order_id,
            "call_id": result.get("call_id"),
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

