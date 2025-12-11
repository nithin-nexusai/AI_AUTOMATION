"""Conversation and Message models."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChannelType(str, enum.Enum):
    """Communication channel type."""

    WHATSAPP = "whatsapp"
    VOICE = "voice"


class ConversationStatus(str, enum.Enum):
    """Conversation status."""

    ACTIVE = "active"
    CLOSED = "closed"
    ESCALATED = "escalated"


class MessageRole(str, enum.Enum):
    """Message sender role."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, enum.Enum):
    """Message content type."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    TEMPLATE = "template"


class Conversation(Base):
    """Chat or call session."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    channel: Mapped[ChannelType] = mapped_column(Enum(ChannelType), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.ACTIVE
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")  # noqa: F821
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", lazy="selectin", order_by="Message.created_at"
    )
    call: Mapped["Call | None"] = relationship(  # noqa: F821
        "Call", back_populates="conversation", uselist=False
    )


class Message(Base):
    """Individual messages within a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.TEXT
    )
    wa_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
