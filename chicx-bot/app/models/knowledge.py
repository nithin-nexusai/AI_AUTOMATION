"""Product, FAQ, and Embedding models for knowledge base."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# pgvector import - requires pgvector extension
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore


class SourceType(str, enum.Enum):
    """Embedding source type."""

    FAQ = "faq"
    PRODUCT = "product"


class Product(Base):
    """Product catalog synced from CHICX."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chicx_product_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    product_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    variants: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class FAQ(Base):
    """FAQ entries for RAG-based question answering."""

    __tablename__ = "faqs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Embedding(Base):
    """Vector embeddings for semantic search using pgvector."""

    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Vector column for pgvector - 1536 dimensions (OpenAI embedding size)
    # Note: This requires the pgvector extension to be enabled in PostgreSQL
    embedding = mapped_column(Vector(1536) if Vector else Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
