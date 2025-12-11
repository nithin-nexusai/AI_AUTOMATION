"""User model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Customer profiles linked to CHICX backend."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chicx_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation", back_populates="user", lazy="selectin"
    )
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order", back_populates="user", lazy="selectin"
    )
    calls: Mapped[list["Call"]] = relationship(  # noqa: F821
        "Call", back_populates="user", lazy="selectin"
    )
