"""Order and OrderEvent models."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    """Order status."""

    PLACED = "placed"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    """Payment status."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class EventSource(str, enum.Enum):
    """Order event source."""

    CHICX = "chicx"
    SHIPROCKET = "shiprocket"


class Order(Base):
    """Order records synced from CHICX backend."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    chicx_order_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PLACED
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    shipping_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    shiprocket_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")  # noqa: F821
    events: Mapped[list["OrderEvent"]] = relationship(
        "OrderEvent", back_populates="order", lazy="selectin", order_by="OrderEvent.created_at"
    )


class OrderEvent(Base):
    """Order status change history from webhooks."""

    __tablename__ = "order_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[EventSource] = mapped_column(Enum(EventSource), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="events")
