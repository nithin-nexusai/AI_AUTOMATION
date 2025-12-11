"""CHICX Backend webhook endpoints for product and order sync.

These endpoints receive data from the CHICX main backend to keep
the bot's database in sync with the latest products, orders, and customers.
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.services.chicx_sync import ChicxSyncService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/chicx", tags=["CHICX Backend"])
settings = get_settings()


def verify_chicx_signature(
    payload: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    """Verify webhook signature from CHICX backend.

    Args:
        payload: Raw request body bytes.
        signature: Signature from X-CHICX-Signature header.
        secret: Shared secret key (CHICX_API_KEY).

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


async def verify_webhook(
    request: Request,
    x_chicx_signature: str | None = Header(None),
) -> bytes:
    """Dependency to verify CHICX webhook signature.

    Args:
        request: FastAPI request object.
        x_chicx_signature: Signature header from CHICX backend.

    Returns:
        Raw request body if valid.

    Raises:
        HTTPException: If signature verification fails.
    """
    body = await request.body()

    # Skip verification in development if no secret configured
    if not settings.chicx_api_key:
        logger.warning("CHICX_API_KEY not configured - skipping signature verification")
        return body

    if not verify_chicx_signature(body, x_chicx_signature, settings.chicx_api_key):
        logger.warning("Invalid CHICX webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body


# =============================================================================
# Product Sync Endpoints
# =============================================================================


@router.post("/products")
async def sync_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _body: bytes = Depends(verify_webhook),
):
    """Receive product catalog updates from CHICX backend.

    Expected payload format (adjust based on actual CHICX API spec):
    {
        "event": "product.created" | "product.updated" | "product.deleted",
        "data": {
            "product_id": "string",
            "name": "string",
            "description": "string",
            "category": "string",
            "price": number,
            "image_url": "string",
            "product_url": "string",
            "variants": {...},
            "is_active": boolean
        }
    }

    For bulk sync:
    {
        "event": "products.bulk_sync",
        "data": {
            "products": [...]
        }
    }
    """
    try:
        payload = await request.json()
        event = payload.get("event", "")
        data = payload.get("data", {})

        logger.info(f"Received CHICX product webhook: {event}")

        sync_service = ChicxSyncService(db)

        if event == "product.created":
            result = await sync_service.create_product(data)
        elif event == "product.updated":
            result = await sync_service.update_product(data)
        elif event == "product.deleted":
            result = await sync_service.delete_product(data.get("product_id"))
        elif event == "products.bulk_sync":
            result = await sync_service.bulk_sync_products(data.get("products", []))
        else:
            logger.warning(f"Unknown product event: {event}")
            return {"status": "ignored", "message": f"Unknown event: {event}"}

        return {"status": "success", "result": result}

    except Exception as e:
        logger.exception(f"Error processing product webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Order Sync Endpoints
# =============================================================================


@router.post("/orders")
async def sync_orders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _body: bytes = Depends(verify_webhook),
):
    """Receive order updates from CHICX backend.

    Expected payload format (adjust based on actual CHICX API spec):
    {
        "event": "order.created" | "order.updated" | "order.status_changed",
        "data": {
            "order_id": "string",
            "customer_phone": "string",
            "customer_email": "string",
            "customer_name": "string",
            "status": "placed" | "confirmed" | "shipped" | "delivered" | "cancelled",
            "total_amount": number,
            "items": [...],
            "shipping_address": {...},
            "payment_method": "string",
            "payment_status": "pending" | "paid" | "failed" | "refunded",
            "tracking_number": "string",
            "placed_at": "ISO datetime"
        }
    }
    """
    try:
        payload = await request.json()
        event = payload.get("event", "")
        data = payload.get("data", {})

        logger.info(f"Received CHICX order webhook: {event}")

        sync_service = ChicxSyncService(db)

        if event == "order.created":
            result = await sync_service.create_order(data)
        elif event == "order.updated":
            result = await sync_service.update_order(data)
        elif event == "order.status_changed":
            result = await sync_service.update_order_status(data)
            # Optionally notify customer via WhatsApp
            # await notify_order_status_change(data)
        else:
            logger.warning(f"Unknown order event: {event}")
            return {"status": "ignored", "message": f"Unknown event: {event}"}

        return {"status": "success", "result": result}

    except Exception as e:
        logger.exception(f"Error processing order webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Customer Sync Endpoints
# =============================================================================


@router.post("/customers")
async def sync_customers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _body: bytes = Depends(verify_webhook),
):
    """Receive customer updates from CHICX backend.

    Expected payload format:
    {
        "event": "customer.created" | "customer.updated",
        "data": {
            "customer_id": "string",
            "phone": "string",
            "email": "string",
            "name": "string"
        }
    }
    """
    try:
        payload = await request.json()
        event = payload.get("event", "")
        data = payload.get("data", {})

        logger.info(f"Received CHICX customer webhook: {event}")

        sync_service = ChicxSyncService(db)

        if event in ("customer.created", "customer.updated"):
            result = await sync_service.upsert_customer(data)
        else:
            logger.warning(f"Unknown customer event: {event}")
            return {"status": "ignored", "message": f"Unknown event: {event}"}

        return {"status": "success", "result": result}

    except Exception as e:
        logger.exception(f"Error processing customer webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def chicx_webhook_health():
    """Health check for CHICX webhook endpoint."""
    return {"status": "ok", "endpoint": "chicx_webhooks"}
