"""FAQ and Embedding models for knowledge base.

Products come from CHICX backend API - no local storage needed.
Only FAQs are stored locally with pgvector embeddings for semantic search.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
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
    """Vector embeddings for semantic search using pgvector.

    Used only for FAQ semantic search.
    """

    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Vector column for pgvector - 1536 dimensions (OpenAI embedding size)
    embedding = mapped_column(Vector(1536) if Vector else Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
