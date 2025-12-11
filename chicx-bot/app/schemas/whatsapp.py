"""Pydantic schemas for WhatsApp webhook payloads.

This module defines the data models for WhatsApp Cloud API webhook payloads,
including message types, status updates, and interactive components.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WebhookVerification(BaseModel):
    """Schema for WhatsApp webhook verification request (GET).

    Meta sends this during webhook setup to verify the endpoint.
    """
    hub_mode: str = Field(alias="hub.mode")
    hub_verify_token: str = Field(alias="hub.verify_token")
    hub_challenge: str = Field(alias="hub.challenge")

    model_config = {"populate_by_name": True}


# ============================================================================
# Message Types
# ============================================================================

class MessageType(str, Enum):
    """Types of WhatsApp messages."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    BUTTON = "button"
    REACTION = "reaction"
    ORDER = "order"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class InteractiveType(str, Enum):
    """Types of interactive messages."""
    BUTTON_REPLY = "button_reply"
    LIST_REPLY = "list_reply"


# ============================================================================
# Text Message
# ============================================================================

class TextMessage(BaseModel):
    """Text message content."""
    body: str


# ============================================================================
# Interactive Message Components
# ============================================================================

class ButtonReply(BaseModel):
    """Button reply from interactive message."""
    id: str
    title: str


class ListReply(BaseModel):
    """List reply from interactive message."""
    id: str
    title: str
    description: str | None = None


class InteractiveMessage(BaseModel):
    """Interactive message content (button or list replies)."""
    type: InteractiveType
    button_reply: ButtonReply | None = None
    list_reply: ListReply | None = None


# ============================================================================
# Image/Media Message
# ============================================================================

class ImageMessage(BaseModel):
    """Image message content."""
    id: str  # Media ID for downloading
    mime_type: str | None = None
    sha256: str | None = None
    caption: str | None = None


class AudioMessage(BaseModel):
    """Audio message content."""
    id: str
    mime_type: str | None = None


class DocumentMessage(BaseModel):
    """Document message content."""
    id: str
    mime_type: str | None = None
    sha256: str | None = None
    caption: str | None = None
    filename: str | None = None


class VideoMessage(BaseModel):
    """Video message content."""
    id: str
    mime_type: str | None = None
    sha256: str | None = None
    caption: str | None = None


# ============================================================================
# Location Message
# ============================================================================

class LocationMessage(BaseModel):
    """Location message content."""
    latitude: float
    longitude: float
    name: str | None = None
    address: str | None = None


# ============================================================================
# Button Message (Template button responses)
# ============================================================================

class ButtonMessage(BaseModel):
    """Button click from template message."""
    text: str
    payload: str


# ============================================================================
# Reaction Message
# ============================================================================

class ReactionMessage(BaseModel):
    """Reaction to a message."""
    message_id: str
    emoji: str


# ============================================================================
# Contact Information
# ============================================================================

class ContactProfile(BaseModel):
    """WhatsApp contact profile information."""
    name: str | None = None


class Contact(BaseModel):
    """Contact information from webhook."""
    wa_id: str
    profile: ContactProfile | None = None


# ============================================================================
# Context (for replies)
# ============================================================================

class MessageContext(BaseModel):
    """Context for message replies."""
    from_: str | None = Field(default=None, alias="from")
    id: str | None = None
    forwarded: bool | None = None
    frequently_forwarded: bool | None = None

    model_config = {"populate_by_name": True}


# ============================================================================
# Error
# ============================================================================

class WebhookError(BaseModel):
    """Error information from webhook."""
    code: int
    title: str
    message: str | None = None
    error_data: dict[str, Any] | None = None


# ============================================================================
# Main Message Schema
# ============================================================================

class Message(BaseModel):
    """Individual message from WhatsApp webhook.

    This represents a single message with its type-specific content.
    """
    id: str
    from_: str = Field(alias="from")  # Sender's phone number
    timestamp: str
    type: MessageType

    # Type-specific content (only one will be present based on type)
    text: TextMessage | None = None
    interactive: InteractiveMessage | None = None
    image: ImageMessage | None = None
    audio: AudioMessage | None = None
    video: VideoMessage | None = None
    document: DocumentMessage | None = None
    location: LocationMessage | None = None
    button: ButtonMessage | None = None
    reaction: ReactionMessage | None = None

    # Context for replies
    context: MessageContext | None = None

    # Error info if message has errors
    errors: list[WebhookError] | None = None

    model_config = {"populate_by_name": True}

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: str) -> MessageType:
        """Convert unknown message types to UNKNOWN."""
        try:
            return MessageType(v)
        except ValueError:
            return MessageType.UNKNOWN

    @property
    def sender_phone(self) -> str:
        """Get the sender's phone number."""
        return self.from_

    @property
    def message_id(self) -> str:
        """Get the WhatsApp message ID."""
        return self.id

    @property
    def timestamp_datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(int(self.timestamp))

    def get_text_content(self) -> str | None:
        """Extract text content from message regardless of type.

        Returns:
            The text content if available, None otherwise.
        """
        if self.type == MessageType.TEXT and self.text:
            return self.text.body
        elif self.type == MessageType.INTERACTIVE and self.interactive:
            if self.interactive.button_reply:
                return self.interactive.button_reply.title
            elif self.interactive.list_reply:
                return self.interactive.list_reply.title
        elif self.type == MessageType.BUTTON and self.button:
            return self.button.text
        elif self.type == MessageType.IMAGE and self.image and self.image.caption:
            return self.image.caption
        return None


# ============================================================================
# Status Updates
# ============================================================================

class StatusType(str, Enum):
    """Types of message status updates."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ConversationOrigin(BaseModel):
    """Origin of the conversation for billing."""
    type: str  # business_initiated, user_initiated, referral_conversion


class Conversation(BaseModel):
    """Conversation info for billing tracking."""
    id: str
    origin: ConversationOrigin | None = None
    expiration_timestamp: str | None = None


class Pricing(BaseModel):
    """Pricing information for the message."""
    billable: bool
    pricing_model: str
    category: str | None = None


class Status(BaseModel):
    """Message status update from webhook."""
    id: str  # Message ID
    status: StatusType
    timestamp: str
    recipient_id: str  # Phone number of recipient
    conversation: Conversation | None = None
    pricing: Pricing | None = None
    errors: list[WebhookError] | None = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> StatusType:
        """Convert status string to enum."""
        try:
            return StatusType(v)
        except ValueError:
            return StatusType.FAILED


# ============================================================================
# Webhook Payload Structure
# ============================================================================

class Metadata(BaseModel):
    """Metadata about the business phone number."""
    display_phone_number: str
    phone_number_id: str


class Value(BaseModel):
    """Value object containing messages or statuses."""
    messaging_product: str
    metadata: Metadata
    contacts: list[Contact] | None = None
    messages: list[Message] | None = None
    statuses: list[Status] | None = None
    errors: list[WebhookError] | None = None


class Change(BaseModel):
    """Change notification from webhook."""
    value: Value
    field: str


class Entry(BaseModel):
    """Entry in the webhook payload."""
    id: str  # WhatsApp Business Account ID
    changes: list[Change]


class WhatsAppWebhookPayload(BaseModel):
    """Root schema for WhatsApp webhook payload.

    This is the main schema for parsing incoming webhook requests.

    Example payload structure:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {...},
                    "contacts": [...],
                    "messages": [...]
                },
                "field": "messages"
            }]
        }]
    }
    """
    object: str
    entry: list[Entry]

    def get_messages(self) -> list[Message]:
        """Extract all messages from the webhook payload.

        Returns:
            List of Message objects from all entries and changes.
        """
        messages: list[Message] = []
        for entry in self.entry:
            for change in entry.changes:
                if change.value.messages:
                    messages.extend(change.value.messages)
        return messages

    def get_statuses(self) -> list[Status]:
        """Extract all status updates from the webhook payload.

        Returns:
            List of Status objects from all entries and changes.
        """
        statuses: list[Status] = []
        for entry in self.entry:
            for change in entry.changes:
                if change.value.statuses:
                    statuses.extend(change.value.statuses)
        return statuses

    def get_contacts(self) -> list[Contact]:
        """Extract all contacts from the webhook payload.

        Returns:
            List of Contact objects from all entries and changes.
        """
        contacts: list[Contact] = []
        for entry in self.entry:
            for change in entry.changes:
                if change.value.contacts:
                    contacts.extend(change.value.contacts)
        return contacts

    def get_phone_number_id(self) -> str | None:
        """Get the business phone number ID from metadata.

        Returns:
            The phone number ID or None if not found.
        """
        for entry in self.entry:
            for change in entry.changes:
                return change.value.metadata.phone_number_id
        return None

    def is_message_webhook(self) -> bool:
        """Check if this webhook contains messages.

        Returns:
            True if the webhook contains at least one message.
        """
        return len(self.get_messages()) > 0

    def is_status_webhook(self) -> bool:
        """Check if this webhook contains status updates.

        Returns:
            True if the webhook contains at least one status update.
        """
        return len(self.get_statuses()) > 0


# ============================================================================
# Outbound Message Schemas (for sending messages)
# ============================================================================

class OutboundTextMessage(BaseModel):
    """Schema for sending a text message."""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str  # Recipient phone number
    type: str = "text"
    text: dict[str, str]  # {"body": "message content"}

    @classmethod
    def create(cls, to: str, body: str, preview_url: bool = False) -> "OutboundTextMessage":
        """Create a text message payload.

        Args:
            to: Recipient phone number
            body: Message text content
            preview_url: Whether to show URL preview

        Returns:
            OutboundTextMessage instance ready for API call.
        """
        text_content: dict[str, Any] = {"body": body}
        if preview_url:
            text_content["preview_url"] = True
        return cls(to=to, text=text_content)


class InteractiveButton(BaseModel):
    """Button for interactive message."""
    type: str = "reply"
    reply: dict[str, str]  # {"id": "btn_id", "title": "Button Text"}


class InteractiveAction(BaseModel):
    """Actions for interactive message."""
    buttons: list[InteractiveButton] | None = None
    button: str | None = None  # For list messages
    sections: list[dict[str, Any]] | None = None  # For list messages


class InteractiveBody(BaseModel):
    """Body for interactive message."""
    text: str


class InteractiveHeader(BaseModel):
    """Header for interactive message."""
    type: str = "text"
    text: str | None = None


class OutboundInteractiveMessage(BaseModel):
    """Schema for sending an interactive message (buttons or list)."""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "interactive"
    interactive: dict[str, Any]

    @classmethod
    def create_button_message(
        cls,
        to: str,
        body: str,
        buttons: list[tuple[str, str]],
        header: str | None = None,
    ) -> "OutboundInteractiveMessage":
        """Create an interactive button message.

        Args:
            to: Recipient phone number
            body: Message body text
            buttons: List of (id, title) tuples for buttons (max 3)
            header: Optional header text

        Returns:
            OutboundInteractiveMessage instance.
        """
        interactive: dict[str, Any] = {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn_id, "title": title}}
                    for btn_id, title in buttons[:3]  # Max 3 buttons
                ]
            }
        }
        if header:
            interactive["header"] = {"type": "text", "text": header}

        return cls(to=to, interactive=interactive)

    @classmethod
    def create_list_message(
        cls,
        to: str,
        body: str,
        button_text: str,
        sections: list[dict[str, Any]],
        header: str | None = None,
    ) -> "OutboundInteractiveMessage":
        """Create an interactive list message.

        Args:
            to: Recipient phone number
            body: Message body text
            button_text: Text for the list button
            sections: List of section objects with rows
            header: Optional header text

        Returns:
            OutboundInteractiveMessage instance.
        """
        interactive: dict[str, Any] = {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": sections,
            }
        }
        if header:
            interactive["header"] = {"type": "text", "text": header}

        return cls(to=to, interactive=interactive)


class TemplateComponent(BaseModel):
    """Component for template message."""
    type: str
    parameters: list[dict[str, Any]] | None = None


class OutboundTemplateMessage(BaseModel):
    """Schema for sending a template message."""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "template"
    template: dict[str, Any]

    @classmethod
    def create(
        cls,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: list[dict[str, Any]] | None = None,
    ) -> "OutboundTemplateMessage":
        """Create a template message payload.

        Args:
            to: Recipient phone number
            template_name: Name of the approved template
            language_code: Language code (default: en)
            components: Optional list of template components

        Returns:
            OutboundTemplateMessage instance.
        """
        template: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template["components"] = components

        return cls(to=to, template=template)


class MarkAsReadPayload(BaseModel):
    """Payload for marking a message as read."""
    messaging_product: str = "whatsapp"
    status: str = "read"
    message_id: str
