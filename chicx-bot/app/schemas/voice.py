"""Pydantic schemas for voice/Bolna webhook payloads."""

from typing import Any
from pydantic import BaseModel, Field


class ConversationWebhookPayload(BaseModel):
    """Webhook payload from Bolna for conversation events.
    
    Bolna sends this when the user speaks and we need to generate a response.
    """
    call_id: str = Field(..., description="Bolna call ID")
    transcript: str = Field(..., description="User's speech (from STT)")
    user_phone: str | None = Field(None, description="Caller's phone number")
    conversation_id: str | None = Field(None, description="Bolna conversation ID")
    agent_id: str | None = Field(None, description="Bolna agent ID")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ConversationWebhookResponse(BaseModel):
    """Response to Bolna conversation webhook.
    
    We return text for Bolna to speak via TTS.
    """
    status: str = Field(default="ok", description="Status of the request")
    response: str = Field(..., description="Text for Bolna to speak")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")

# Made with Bob
