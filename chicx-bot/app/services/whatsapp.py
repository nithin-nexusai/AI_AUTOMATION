"""WhatsApp service for message processing and sending.

This module handles:
- Processing incoming WhatsApp messages
- Sending messages via Meta Cloud API (text, templates, interactive)
- Integrating with the LLM client for generating responses
- Managing conversation context in Redis
- Message deduplication using wa_message_id

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.llm import get_llm_client, DeepSeekClient, LLMError
from app.core.prompts import get_system_prompt
from app.core.tools import get_tool_definitions, validate_tool_arguments, ToolName
from app.models.user import User
from app.models.conversation import (
    Conversation,
    Message as MessageModel,
    ChannelType,
    ConversationStatus,
    MessageRole,
    MessageType as DBMessageType,
)
from app.schemas.whatsapp import (
    Message,
    MessageType,
    OutboundTextMessage,
    OutboundInteractiveMessage,
    OutboundTemplateMessage,
    MarkAsReadPayload,
    Status,
    StatusType,
)

logger = logging.getLogger(__name__)

# Constants
WHATSAPP_API_VERSION = "v18.0"
WHATSAPP_API_BASE_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
CONVERSATION_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CONTEXT_MESSAGE_LIMIT = 20  # Max messages to include in LLM context
MESSAGE_DEDUP_TTL_SECONDS = 5 * 60  # 5 minutes for deduplication


class WhatsAppServiceError(Exception):
    """Base exception for WhatsApp service errors."""
    pass


class MessageSendError(WhatsAppServiceError):
    """Raised when message sending fails."""
    pass


class ChicxToolExecutor:
    """Tool executor for CHICX bot LLM function calling.

    This class handles the execution of tools called by the LLM,
    including product search, order tracking, and FAQ queries.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        user_phone: str,
        user_id: uuid.UUID | None = None,
    ) -> None:
        """Initialize the tool executor.

        Args:
            db: Async database session
            redis_client: Redis client for caching
            user_phone: Phone number of the user
            user_id: Optional user ID for order queries
        """
        self._db = db
        self._redis = redis_client
        self._user_phone = user_phone
        self._user_id = user_id
        self._settings = get_settings()

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool

        Returns:
            Dictionary containing the tool execution result
        """
        # Validate arguments
        is_valid, error_msg = validate_tool_arguments(tool_name, arguments)
        if not is_valid:
            logger.warning(f"Invalid tool arguments: {error_msg}")
            return {"error": error_msg}

        try:
            if tool_name == ToolName.SEARCH_PRODUCTS:
                return await self._search_products(arguments)
            elif tool_name == ToolName.GET_PRODUCT_DETAILS:
                return await self._get_product_details(arguments)
            elif tool_name == ToolName.GET_ORDER_STATUS:
                return await self._get_order_status(arguments)
            elif tool_name == ToolName.GET_ORDER_HISTORY:
                return await self._get_order_history(arguments)
            elif tool_name == ToolName.SEARCH_FAQ:
                return await self._search_faq(arguments)
            else:
                logger.error(f"Unknown tool: {tool_name}")
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {e}")
            return {"error": f"Failed to execute {tool_name}: {str(e)}"}

    async def _search_products(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search products in the catalog.

        This is a placeholder - implement with actual product search logic.
        """
        # TODO: Implement actual product search using database/external API
        query = args.get("query", "")
        category = args.get("category")
        min_price = args.get("min_price")
        max_price = args.get("max_price")
        limit = args.get("limit", 5)

        logger.info(
            f"Searching products: query={query}, category={category}, "
            f"price_range={min_price}-{max_price}, limit={limit}"
        )

        # Placeholder response - replace with actual implementation
        return {
            "products": [],
            "total_count": 0,
            "has_more": False,
            "message": "Product search is being set up. Please visit chicx.in to browse products.",
        }

    async def _get_product_details(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get details of a specific product."""
        product_id = args["product_id"]

        logger.info(f"Getting product details: product_id={product_id}")

        # TODO: Implement actual product lookup
        return {
            "error": "product_not_found",
            "message": f"Product {product_id} not found. Please check the product ID.",
        }

    async def _get_order_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get order status and tracking information."""
        order_id = args["order_id"]

        logger.info(f"Getting order status: order_id={order_id}")

        # TODO: Implement actual order lookup from database/CHICX API
        return {
            "error": "order_not_found",
            "message": f"Order {order_id} not found. Please check the order ID from your confirmation email.",
        }

    async def _get_order_history(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get user's order history."""
        limit = args.get("limit", 5)
        status_filter = args.get("status_filter")

        logger.info(
            f"Getting order history: user_phone={self._user_phone}, "
            f"limit={limit}, status_filter={status_filter}"
        )

        # TODO: Implement actual order history lookup
        return {
            "orders": [],
            "total_orders": 0,
            "message": "No orders found for this phone number. Have you made a purchase on chicx.in?",
        }

    async def _search_faq(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search FAQs using semantic search."""
        query = args["query"]
        category = args.get("category")
        limit = args.get("limit", 3)

        logger.info(f"Searching FAQs: query={query}, category={category}, limit={limit}")

        # TODO: Implement actual FAQ search using pgvector
        return {
            "faqs": [],
            "message": "For detailed help, please contact support@chicx.in",
        }


class WhatsAppService:
    """Service for handling WhatsApp message processing and sending.

    This service:
    - Processes incoming messages through the LLM
    - Manages conversation context in Redis
    - Sends messages via the Meta Cloud API
    - Handles message deduplication
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
    ) -> None:
        """Initialize the WhatsApp service.

        Args:
            db: Async database session
            redis_client: Redis client for context management
        """
        self._db = db
        self._redis = redis_client
        self._settings = get_settings()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client for API calls."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._settings.whatsapp_access_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # ========================================================================
    # Signature Verification
    # ========================================================================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify the webhook signature from Meta.

        Args:
            payload: Raw request body bytes
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid, False otherwise
        """
        if not self._settings.whatsapp_app_secret:
            logger.warning("WHATSAPP_APP_SECRET not configured, skipping signature verification")
            return True

        if not signature or not signature.startswith("sha256="):
            logger.warning("Invalid signature format")
            return False

        expected_signature = signature[7:]  # Remove "sha256=" prefix

        computed_signature = hmac.new(
            key=self._settings.whatsapp_app_secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(computed_signature, expected_signature)

        if not is_valid:
            logger.warning("Webhook signature verification failed")

        return is_valid

    # ========================================================================
    # Message Deduplication
    # ========================================================================

    async def is_duplicate_message(self, wa_message_id: str) -> bool:
        """Check if a message has already been processed.

        Args:
            wa_message_id: WhatsApp message ID

        Returns:
            True if message was already processed, False otherwise
        """
        key = f"wa:msg:processed:{wa_message_id}"
        exists = await self._redis.exists(key)
        return bool(exists)

    async def mark_message_processed(self, wa_message_id: str) -> None:
        """Mark a message as processed for deduplication.

        Args:
            wa_message_id: WhatsApp message ID
        """
        key = f"wa:msg:processed:{wa_message_id}"
        await self._redis.setex(key, MESSAGE_DEDUP_TTL_SECONDS, "1")

    # ========================================================================
    # User Management
    # ========================================================================

    async def get_or_create_user(self, phone: str) -> User:
        """Get existing user or create a new one.

        Args:
            phone: User's phone number

        Returns:
            User model instance
        """
        # Normalize phone number (ensure it starts with country code)
        normalized_phone = phone.lstrip("+")

        # Try to find existing user
        result = await self._db.execute(
            select(User).where(User.phone == normalized_phone)
        )
        user = result.scalar_one_or_none()

        if user is None:
            # Create new user
            user = User(phone=normalized_phone)
            self._db.add(user)
            await self._db.flush()
            logger.info(f"Created new user: phone={normalized_phone}, id={user.id}")

        return user

    # ========================================================================
    # Conversation Management
    # ========================================================================

    async def get_or_create_conversation(
        self,
        user: User,
        channel: ChannelType = ChannelType.WHATSAPP,
    ) -> Conversation:
        """Get active conversation or create a new one.

        Args:
            user: User model instance
            channel: Communication channel type

        Returns:
            Conversation model instance
        """
        # Look for active conversation in last 24 hours
        result = await self._db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user.id,
                Conversation.channel == channel,
                Conversation.status == ConversationStatus.ACTIVE,
            )
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            # Create new conversation
            conversation = Conversation(
                user_id=user.id,
                channel=channel,
                status=ConversationStatus.ACTIVE,
            )
            self._db.add(conversation)
            await self._db.flush()
            logger.info(
                f"Created new conversation: user_id={user.id}, conversation_id={conversation.id}"
            )

        return conversation

    async def save_message(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
        message_type: DBMessageType = DBMessageType.TEXT,
        wa_message_id: str | None = None,
    ) -> MessageModel:
        """Save a message to the database.

        Args:
            conversation: Conversation model instance
            role: Message role (user, assistant, system)
            content: Message content
            message_type: Type of message content
            wa_message_id: Optional WhatsApp message ID

        Returns:
            MessageModel instance
        """
        message = MessageModel(
            conversation_id=conversation.id,
            role=role,
            content=content,
            message_type=message_type,
            wa_message_id=wa_message_id,
        )
        self._db.add(message)
        await self._db.flush()
        return message

    # ========================================================================
    # Context Management (Redis)
    # ========================================================================

    def _get_context_key(self, user_phone: str) -> str:
        """Get Redis key for conversation context."""
        return f"wa:context:{user_phone}"

    async def get_conversation_context(
        self,
        user_phone: str,
    ) -> list[dict[str, str]]:
        """Get conversation context from Redis.

        Args:
            user_phone: User's phone number

        Returns:
            List of message dicts with role and content
        """
        key = self._get_context_key(user_phone)
        context_json = await self._redis.get(key)

        if context_json:
            try:
                return json.loads(context_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse context for {user_phone}")

        return []

    async def update_conversation_context(
        self,
        user_phone: str,
        messages: list[dict[str, str]],
    ) -> None:
        """Update conversation context in Redis.

        Args:
            user_phone: User's phone number
            messages: List of message dicts with role and content
        """
        key = self._get_context_key(user_phone)

        # Limit context size
        limited_messages = messages[-CONTEXT_MESSAGE_LIMIT:]

        await self._redis.setex(
            key,
            CONVERSATION_TTL_SECONDS,
            json.dumps(limited_messages),
        )

    async def add_to_context(
        self,
        user_phone: str,
        role: str,
        content: str,
    ) -> list[dict[str, str]]:
        """Add a message to the conversation context.

        Args:
            user_phone: User's phone number
            role: Message role (user, assistant)
            content: Message content

        Returns:
            Updated context list
        """
        context = await self.get_conversation_context(user_phone)
        context.append({"role": role, "content": content})
        await self.update_conversation_context(user_phone, context)
        return context

    # ========================================================================
    # Message Processing
    # ========================================================================

    async def process_message(
        self,
        message: Message,
    ) -> str | None:
        """Process an incoming WhatsApp message.

        This method:
        1. Checks for duplicate messages
        2. Gets or creates user and conversation
        3. Extracts message content
        4. Sends to LLM for response
        5. Sends response back to user

        Args:
            message: Parsed WhatsApp message

        Returns:
            Assistant's response text, or None if message was skipped
        """
        wa_message_id = message.message_id
        sender_phone = message.sender_phone

        logger.info(
            f"Processing message: id={wa_message_id}, from={sender_phone}, type={message.type}"
        )

        # Check for duplicate
        if await self.is_duplicate_message(wa_message_id):
            logger.info(f"Skipping duplicate message: {wa_message_id}")
            return None

        # Mark as processed immediately to prevent race conditions
        await self.mark_message_processed(wa_message_id)

        # Get or create user
        user = await self.get_or_create_user(sender_phone)

        # Get or create conversation
        conversation = await self.get_or_create_conversation(user)

        # Extract text content
        user_text = message.get_text_content()

        if not user_text:
            # Handle non-text messages
            if message.type == MessageType.IMAGE:
                user_text = "[User sent an image]"
                if message.image and message.image.caption:
                    user_text = message.image.caption
            elif message.type == MessageType.AUDIO:
                user_text = "[User sent an audio message]"
            elif message.type == MessageType.LOCATION:
                user_text = "[User shared a location]"
            else:
                user_text = "[User sent a message that I cannot read]"

        # Save user message to database
        await self.save_message(
            conversation=conversation,
            role=MessageRole.USER,
            content=user_text,
            wa_message_id=wa_message_id,
        )

        # Mark message as read
        await self.mark_as_read(wa_message_id)

        # Get LLM response
        try:
            response_text = await self._get_llm_response(
                user_phone=sender_phone,
                user_message=user_text,
                user_id=user.id,
            )
        except Exception as e:
            logger.exception(f"Error getting LLM response: {e}")
            response_text = (
                "I'm having trouble processing your message right now. "
                "Please try again in a moment or contact support@chicx.in for help."
            )

        # Save assistant message to database
        await self.save_message(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )

        # Send response to user
        await self.send_text_message(sender_phone, response_text)

        return response_text

    async def _get_llm_response(
        self,
        user_phone: str,
        user_message: str,
        user_id: uuid.UUID | None = None,
    ) -> str:
        """Get response from LLM with tool calling.

        Args:
            user_phone: User's phone number
            user_message: User's message text
            user_id: Optional user ID for tool context

        Returns:
            Assistant's response text
        """
        # Get conversation context
        context = await self.get_conversation_context(user_phone)

        # Build messages list with system prompt
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": get_system_prompt("whatsapp")},
        ]

        # Add context messages
        messages.extend(context)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Get LLM client
        llm_client: DeepSeekClient = get_llm_client()

        # Create tool executor
        tool_executor = ChicxToolExecutor(
            db=self._db,
            redis_client=self._redis,
            user_phone=user_phone,
            user_id=user_id,
        )

        # Get response with tool calling
        try:
            result = await llm_client.chat_with_tools(
                messages=messages,
                tools=get_tool_definitions(),
                tool_executor=tool_executor,
                max_iterations=5,
                temperature=0.7,
            )

            response_text = result["content"] or "I apologize, I couldn't generate a response."

            # Update context with new messages
            await self.add_to_context(user_phone, "user", user_message)
            await self.add_to_context(user_phone, "assistant", response_text)

            logger.info(
                f"LLM response generated: iterations={result['iterations']}, "
                f"tools_used={len(result['tool_calls_made'])}"
            )

            return response_text

        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise

    async def process_status_update(self, status: Status) -> None:
        """Process a message status update.

        Args:
            status: Status update object
        """
        logger.info(
            f"Status update: message_id={status.id}, status={status.status}, "
            f"recipient={status.recipient_id}"
        )

        # Handle failed messages
        if status.status == StatusType.FAILED:
            logger.error(
                f"Message delivery failed: message_id={status.id}, "
                f"errors={status.errors}"
            )
            # TODO: Implement retry logic or notification

    # ========================================================================
    # Message Sending
    # ========================================================================

    async def _send_api_request(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a request to the WhatsApp API.

        Args:
            payload: Request payload

        Returns:
            API response as dict

        Raises:
            MessageSendError: If the request fails
        """
        url = f"{WHATSAPP_API_BASE_URL}/{self._settings.whatsapp_phone_number_id}/messages"

        client = await self._get_http_client()

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"WhatsApp API error: status={e.response.status_code}, "
                f"body={e.response.text}"
            )
            raise MessageSendError(
                f"Failed to send message: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"WhatsApp API request error: {e}")
            raise MessageSendError(f"Failed to connect to WhatsApp API: {e}") from e

    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> dict[str, Any]:
        """Send a text message.

        Args:
            to: Recipient phone number
            text: Message text
            preview_url: Whether to show URL preview

        Returns:
            API response
        """
        # WhatsApp has a 4096 character limit per message
        if len(text) > 4096:
            # Split into multiple messages
            chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
            result = {}
            for chunk in chunks:
                payload = OutboundTextMessage.create(to, chunk, preview_url)
                result = await self._send_api_request(payload.model_dump())
            return result
        else:
            payload = OutboundTextMessage.create(to, text, preview_url)
            return await self._send_api_request(payload.model_dump())

    async def send_interactive_buttons(
        self,
        to: str,
        body: str,
        buttons: list[tuple[str, str]],
        header: str | None = None,
    ) -> dict[str, Any]:
        """Send an interactive button message.

        Args:
            to: Recipient phone number
            body: Message body text
            buttons: List of (id, title) tuples (max 3)
            header: Optional header text

        Returns:
            API response
        """
        payload = OutboundInteractiveMessage.create_button_message(
            to=to,
            body=body,
            buttons=buttons,
            header=header,
        )
        return await self._send_api_request(payload.model_dump())

    async def send_interactive_list(
        self,
        to: str,
        body: str,
        button_text: str,
        sections: list[dict[str, Any]],
        header: str | None = None,
    ) -> dict[str, Any]:
        """Send an interactive list message.

        Args:
            to: Recipient phone number
            body: Message body text
            button_text: Text for the list button
            sections: List of section objects
            header: Optional header text

        Returns:
            API response
        """
        payload = OutboundInteractiveMessage.create_list_message(
            to=to,
            body=body,
            button_text=button_text,
            sections=sections,
            header=header,
        )
        return await self._send_api_request(payload.model_dump())

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a template message.

        Args:
            to: Recipient phone number
            template_name: Name of the approved template
            language_code: Language code
            components: Optional template components

        Returns:
            API response
        """
        payload = OutboundTemplateMessage.create(
            to=to,
            template_name=template_name,
            language_code=language_code,
            components=components,
        )
        return await self._send_api_request(payload.model_dump())

    async def mark_as_read(self, message_id: str) -> dict[str, Any] | None:
        """Mark a message as read.

        Args:
            message_id: WhatsApp message ID

        Returns:
            API response or None if it fails
        """
        url = f"{WHATSAPP_API_BASE_URL}/{self._settings.whatsapp_phone_number_id}/messages"

        payload = MarkAsReadPayload(message_id=message_id)
        client = await self._get_http_client()

        try:
            response = await client.post(url, json=payload.model_dump())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to mark message as read: {e}")
            return None


# Factory function for dependency injection
async def get_whatsapp_service(
    db: AsyncSession,
    redis_client: redis.Redis,
) -> WhatsAppService:
    """Create a WhatsApp service instance.

    Args:
        db: Database session
        redis_client: Redis client

    Returns:
        WhatsAppService instance
    """
    return WhatsAppService(db=db, redis_client=redis_client)
