"""Service for syncing data from CHICX backend.

This service handles product, order, and customer synchronization
from the CHICX main backend to the bot's local database.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Product
from app.models.order import Order, OrderEvent, OrderStatus, PaymentStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class ChicxSyncService:
    """Service for syncing CHICX backend data to local database.

    This service receives data from CHICX backend webhooks and
    maintains a local copy for the bot to query.

    Attributes:
        db: Async SQLAlchemy session.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the sync service.

        Args:
            db: Async database session.
        """
        self._db = db

    # =========================================================================
    # Product Sync
    # =========================================================================

    async def create_product(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new product from CHICX backend data.

        Args:
            data: Product data from webhook.
                Expected keys: product_id, name, description, category,
                price, image_url, product_url, variants, is_active

        Returns:
            Dict with created product info.
        """
        product_id = data.get("product_id")
        if not product_id:
            raise ValueError("product_id is required")

        # Check if product already exists
        existing = await self._get_product_by_chicx_id(product_id)
        if existing:
            return await self.update_product(data)

        product = Product(
            chicx_product_id=product_id,
            name=data.get("name", ""),
            description=data.get("description"),
            category=data.get("category"),
            price=Decimal(str(data.get("price", 0))),
            image_url=data.get("image_url"),
            product_url=data.get("product_url"),
            variants=data.get("variants"),
            is_active=data.get("is_active", True),
            synced_at=datetime.now(timezone.utc),
        )

        self._db.add(product)
        await self._db.commit()

        logger.info(f"Created product: {product_id} - {product.name}")
        return {"action": "created", "product_id": product_id}

    async def update_product(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing product.

        Args:
            data: Product data from webhook.

        Returns:
            Dict with update result.
        """
        product_id = data.get("product_id")
        if not product_id:
            raise ValueError("product_id is required")

        product = await self._get_product_by_chicx_id(product_id)
        if not product:
            return await self.create_product(data)

        # Update fields if provided
        if "name" in data:
            product.name = data["name"]
        if "description" in data:
            product.description = data["description"]
        if "category" in data:
            product.category = data["category"]
        if "price" in data:
            product.price = Decimal(str(data["price"]))
        if "image_url" in data:
            product.image_url = data["image_url"]
        if "product_url" in data:
            product.product_url = data["product_url"]
        if "variants" in data:
            product.variants = data["variants"]
        if "is_active" in data:
            product.is_active = data["is_active"]

        product.synced_at = datetime.now(timezone.utc)

        await self._db.commit()

        logger.info(f"Updated product: {product_id}")
        return {"action": "updated", "product_id": product_id}

    async def delete_product(self, product_id: str | None) -> dict[str, Any]:
        """Soft delete a product (mark as inactive).

        Args:
            product_id: CHICX product ID to delete.

        Returns:
            Dict with delete result.
        """
        if not product_id:
            raise ValueError("product_id is required")

        product = await self._get_product_by_chicx_id(product_id)
        if not product:
            return {"action": "not_found", "product_id": product_id}

        product.is_active = False
        product.synced_at = datetime.now(timezone.utc)

        await self._db.commit()

        logger.info(f"Deleted (soft) product: {product_id}")
        return {"action": "deleted", "product_id": product_id}

    async def bulk_sync_products(self, products: list[dict[str, Any]]) -> dict[str, Any]:
        """Bulk sync products from CHICX backend.

        Args:
            products: List of product data dicts.

        Returns:
            Dict with sync results.
        """
        created = 0
        updated = 0
        errors = 0

        for product_data in products:
            try:
                product_id = product_data.get("product_id")
                existing = await self._get_product_by_chicx_id(product_id)

                if existing:
                    await self.update_product(product_data)
                    updated += 1
                else:
                    await self.create_product(product_data)
                    created += 1

            except Exception as e:
                logger.error(f"Error syncing product {product_data.get('product_id')}: {e}")
                errors += 1

        logger.info(f"Bulk sync complete: {created} created, {updated} updated, {errors} errors")
        return {"created": created, "updated": updated, "errors": errors}

    async def _get_product_by_chicx_id(self, chicx_product_id: str) -> Product | None:
        """Get product by CHICX product ID.

        Args:
            chicx_product_id: The CHICX product identifier.

        Returns:
            Product instance or None.
        """
        stmt = select(Product).where(Product.chicx_product_id == chicx_product_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    # =========================================================================
    # Order Sync
    # =========================================================================

    async def create_order(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new order from CHICX backend data.

        Args:
            data: Order data from webhook.
                Expected keys: order_id, customer_phone, customer_email,
                customer_name, status, total_amount, items, shipping_address,
                payment_method, payment_status, tracking_number, placed_at

        Returns:
            Dict with created order info.
        """
        order_id = data.get("order_id")
        if not order_id:
            raise ValueError("order_id is required")

        # Check if order already exists
        existing = await self._get_order_by_chicx_id(order_id)
        if existing:
            return await self.update_order(data)

        # Get or create user
        user = await self._get_or_create_user(data)

        # Parse status
        status = self._parse_order_status(data.get("status", "placed"))
        payment_status = self._parse_payment_status(data.get("payment_status", "pending"))

        # Parse placed_at datetime
        placed_at = data.get("placed_at")
        if isinstance(placed_at, str):
            placed_at = datetime.fromisoformat(placed_at.replace("Z", "+00:00"))
        elif not placed_at:
            placed_at = datetime.now(timezone.utc)

        order = Order(
            user_id=user.id,
            chicx_order_id=order_id,
            status=status,
            total_amount=Decimal(str(data.get("total_amount", 0))),
            item_count=len(data.get("items", [])),
            items=data.get("items"),
            shipping_address=data.get("shipping_address"),
            payment_method=data.get("payment_method"),
            payment_status=payment_status,
            tracking_number=data.get("tracking_number"),
            placed_at=placed_at,
        )

        self._db.add(order)

        # Create initial order event
        event = OrderEvent(
            order=order,
            status=status.value,
            source="chicx",
            payload={"event": "order.created"},
        )
        self._db.add(event)

        await self._db.commit()

        logger.info(f"Created order: {order_id} for user {user.phone}")
        return {"action": "created", "order_id": order_id}

    async def update_order(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing order.

        Args:
            data: Order data from webhook.

        Returns:
            Dict with update result.
        """
        order_id = data.get("order_id")
        if not order_id:
            raise ValueError("order_id is required")

        order = await self._get_order_by_chicx_id(order_id)
        if not order:
            return await self.create_order(data)

        # Update fields if provided
        if "status" in data:
            order.status = self._parse_order_status(data["status"])
        if "total_amount" in data:
            order.total_amount = Decimal(str(data["total_amount"]))
        if "items" in data:
            order.items = data["items"]
            order.item_count = len(data["items"])
        if "shipping_address" in data:
            order.shipping_address = data["shipping_address"]
        if "payment_method" in data:
            order.payment_method = data["payment_method"]
        if "payment_status" in data:
            order.payment_status = self._parse_payment_status(data["payment_status"])
        if "tracking_number" in data:
            order.tracking_number = data["tracking_number"]
        if "shiprocket_order_id" in data:
            order.shiprocket_order_id = data["shiprocket_order_id"]

        await self._db.commit()

        logger.info(f"Updated order: {order_id}")
        return {"action": "updated", "order_id": order_id}

    async def update_order_status(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update order status and create an event.

        Args:
            data: Status update data.
                Expected keys: order_id, status, tracking_number (optional)

        Returns:
            Dict with update result.
        """
        order_id = data.get("order_id")
        if not order_id:
            raise ValueError("order_id is required")

        order = await self._get_order_by_chicx_id(order_id)
        if not order:
            logger.warning(f"Order not found for status update: {order_id}")
            return {"action": "not_found", "order_id": order_id}

        new_status = self._parse_order_status(data.get("status", ""))
        old_status = order.status

        order.status = new_status

        if "tracking_number" in data:
            order.tracking_number = data["tracking_number"]

        # Set delivered_at if status is delivered
        if new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.now(timezone.utc)

        # Create order event
        event = OrderEvent(
            order=order,
            status=new_status.value,
            source="chicx",
            payload={
                "event": "order.status_changed",
                "old_status": old_status.value,
                "new_status": new_status.value,
            },
        )
        self._db.add(event)

        await self._db.commit()

        logger.info(f"Order {order_id} status changed: {old_status.value} -> {new_status.value}")
        return {
            "action": "status_updated",
            "order_id": order_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
        }

    async def _get_order_by_chicx_id(self, chicx_order_id: str) -> Order | None:
        """Get order by CHICX order ID.

        Args:
            chicx_order_id: The CHICX order identifier.

        Returns:
            Order instance or None.
        """
        stmt = select(Order).where(Order.chicx_order_id == chicx_order_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    def _parse_order_status(self, status: str) -> OrderStatus:
        """Parse order status string to enum.

        Args:
            status: Status string from webhook.

        Returns:
            OrderStatus enum value.
        """
        status_map = {
            "placed": OrderStatus.PLACED,
            "confirmed": OrderStatus.CONFIRMED,
            "shipped": OrderStatus.SHIPPED,
            "out_for_delivery": OrderStatus.OUT_FOR_DELIVERY,
            "delivered": OrderStatus.DELIVERED,
            "cancelled": OrderStatus.CANCELLED,
        }
        return status_map.get(status.lower(), OrderStatus.PLACED)

    def _parse_payment_status(self, status: str) -> PaymentStatus:
        """Parse payment status string to enum.

        Args:
            status: Payment status string from webhook.

        Returns:
            PaymentStatus enum value.
        """
        status_map = {
            "pending": PaymentStatus.PENDING,
            "paid": PaymentStatus.PAID,
            "failed": PaymentStatus.FAILED,
            "refunded": PaymentStatus.REFUNDED,
        }
        return status_map.get(status.lower(), PaymentStatus.PENDING)

    # =========================================================================
    # Customer Sync
    # =========================================================================

    async def upsert_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create or update a customer.

        Args:
            data: Customer data from webhook.
                Expected keys: customer_id, phone, email, name

        Returns:
            Dict with upsert result.
        """
        phone = data.get("phone")
        if not phone:
            raise ValueError("phone is required")

        # Normalize phone number
        phone = self._normalize_phone(phone)

        user = await self._get_user_by_phone(phone)

        if user:
            # Update existing user
            if "email" in data:
                user.email = data["email"]
            if "name" in data:
                user.name = data["name"]
            if "customer_id" in data:
                user.chicx_customer_id = data["customer_id"]

            await self._db.commit()
            logger.info(f"Updated customer: {phone}")
            return {"action": "updated", "phone": phone}
        else:
            # Create new user
            user = User(
                phone=phone,
                email=data.get("email"),
                name=data.get("name"),
                chicx_customer_id=data.get("customer_id"),
            )
            self._db.add(user)
            await self._db.commit()

            logger.info(f"Created customer: {phone}")
            return {"action": "created", "phone": phone}

    async def _get_or_create_user(self, data: dict[str, Any]) -> User:
        """Get or create user from order data.

        Args:
            data: Order data containing customer info.

        Returns:
            User instance.
        """
        phone = data.get("customer_phone")
        if not phone:
            raise ValueError("customer_phone is required")

        phone = self._normalize_phone(phone)
        user = await self._get_user_by_phone(phone)

        if not user:
            user = User(
                phone=phone,
                email=data.get("customer_email"),
                name=data.get("customer_name"),
            )
            self._db.add(user)
            await self._db.flush()

        return user

    async def _get_user_by_phone(self, phone: str) -> User | None:
        """Get user by phone number.

        Args:
            phone: Normalized phone number.

        Returns:
            User instance or None.
        """
        stmt = select(User).where(User.phone == phone)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to consistent format.

        Args:
            phone: Raw phone number.

        Returns:
            Normalized phone number (e.g., +919876543210).
        """
        # Remove spaces, dashes, parentheses
        phone = "".join(c for c in phone if c.isdigit() or c == "+")

        # Add country code if missing
        if not phone.startswith("+"):
            if phone.startswith("91") and len(phone) == 12:
                phone = "+" + phone
            elif len(phone) == 10:
                phone = "+91" + phone

        return phone
