"""Call and CallTranscript models for voice agent."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CallDirection(str, enum.Enum):
    """Call direction."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, enum.Enum):
    """Call status/outcome."""

    RESOLVED = "resolved"  # Bot handled successfully
    ESCALATED = "escalated"  # Transferred to human
    MISSED = "missed"  # Call not answered
    FAILED = "failed"  # Technical error


class Call(Base):
    """Voice call records linked to conversations."""

    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exotel_call_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    bolna_call_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    direction: Mapped[CallDirection] = mapped_column(
        Enum(CallDirection), default=CallDirection.INBOUND
    )
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus), default=CallStatus.RESOLVED
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g., "ta", "hi", "en"
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation: Mapped["Conversation | None"] = relationship(  # noqa: F821
        "Conversation", back_populates="call"
    )
    user: Mapped["User | None"] = relationship("User", back_populates="calls")  # noqa: F821
    transcript: Mapped["CallTranscript | None"] = relationship(
        "CallTranscript", back_populates="call", uselist=False
    )


class CallTranscript(Base):
    """Full transcripts of voice calls."""

    __tablename__ = "call_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id"), unique=True, nullable=False
    )
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    segments: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="transcript")
