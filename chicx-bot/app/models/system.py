"""System models: Templates, Analytics, and Search Logs."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TemplateType(str, enum.Enum):
    """WhatsApp template type."""

    UTILITY = "utility"
    MARKETING = "marketing"


class TemplateStatus(str, enum.Enum):
    """WhatsApp template approval status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Template(Base):
    """WhatsApp message templates."""

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[TemplateType] = mapped_column(Enum(TemplateType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus), default=TemplateStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AnalyticsEvent(Base):
    """Event tracking for analytics."""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class SearchLog(Base):
    """Log of product searches for catalog gap analysis.

    Tracks searches that returned no results to identify missing products.
    Used by the Catalog Gaps dashboard screen.
    """

    __tablename__ = "search_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g., "en", "hi", "ta"
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
