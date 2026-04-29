"""Voice conversation orchestrator for Bolna integration.

This service handles LLM conversation flow for voice calls, using Bolna only for:
- Speech-to-text (STT)
- Text-to-speech (TTS)
- Call management

The orchestrator owns the LLM orchestration and tool execution, providing
full control over the conversation flow while keeping Bolna's excellent
voice quality.

Architecture:
    User speaks → Bolna STT → Webhook → VoiceOrchestrator
                                            ↓
                                    LLM + Tool Execution
                                            ↓
                                    Response Text
                                            ↓
                                    Bolna TTS → User hears
"""

import json
import logging
from typing import Any

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.llm import get_llm_client, OpenRouterClient, LLMError, ToolExecutor
from app.core.prompts import get_system_prompt
from app.core.tools import get_tool_definitions, validate_tool_arguments, ToolName
from app.models.user import User
from app.models.conversation import (
    Conversation,
    Message as MessageModel,
    ChannelType,
    ConversationStatus,
    MessageRole,
)
from app.services.embedding import EmbeddingService
from app.services.chicx_api import get_chicx_client, ChicxAPIError
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)

# Constants
CONVERSATION_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CONTEXT_MESSAGE_LIMIT = 20  # Max messages to include in LLM context


class VoiceOrchestratorError(Exception):
    """Base exception for voice orchestrator errors."""
    pass


class VoiceOrchestrator:
    """Orchestrates voice conversations with LLM and tools.
    
    This class manages the conversation flow for voice calls:
    1. Receives transcripts from Bolna
    2. Loads conversation context from Redis
    3. Processes with LLM and executes tools
    4. Saves updated context
    5. Returns response text for Bolna to speak
    
    The orchestrator reuses the proven LLM orchestration pattern from
    WhatsApp integration, ensuring consistent behavior across channels.
    """

    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        """Initialize the voice orchestrator.
        
        Args:
            db: Async database session
            redis_client: Redis client for context storage
        """
        self._db = db
        self._redis = redis_client
        self._llm = get_llm_client()
        self._tools = get_tool_definitions()
        self._settings = get_settings()

    async def process_transcript(
        self,
        call_id: str,
        transcript: str,
        user_phone: str,
    ) -> str:
        """Process voice transcript and generate response.
        
        This is the main entry point for processing voice conversations.
        It handles the complete flow from transcript to response.
        
        Args:
            call_id: Bolna call ID (used as context key)
            transcript: User's speech (from Bolna STT)
            user_phone: Caller's phone number (for tool authorization)
            
        Returns:
            Text response to be spoken by Bolna TTS
            
        Raises:
            VoiceOrchestratorError: If processing fails
        """
        try:
            logger.info(
                f"Processing voice transcript: call_id={call_id}, "
                f"phone={user_phone}, transcript_length={len(transcript)}"
            )

            # 1. Load conversation context from Redis
            messages = await self._load_context(call_id)
            
            # 2. Add user message
            messages.append({
                "role": "user",
                "content": transcript
            })
            
            # 3. Execute LLM with tools
            tool_executor = VoiceToolExecutor(
                db=self._db,
                redis_client=self._redis,
                user_phone=user_phone,
            )
            
            # Use the proven chat_with_tools method (same as WhatsApp!)
            response = await self._llm.chat_with_tools(
                messages=messages,
                tools=self._tools,
                tool_executor=tool_executor,
                max_iterations=5,
                temperature=0.7,
            )
            
            # 4. Add assistant response to context
            messages.append({
                "role": "assistant",
                "content": response["content"]
            })
            
            # 5. Save updated context to Redis
            await self._save_context(call_id, messages)
            
            # 6. Log analytics
            logger.info(
                f"Voice response generated: call_id={call_id}, "
                f"tool_calls={len(response.get('tool_calls_made', []))}, "
                f"iterations={response.get('iterations', 0)}"
            )
            
            # 7. Return text for Bolna to speak
            return response["content"]
            
        except LLMError as e:
            logger.error(f"LLM error processing transcript: {e}")
            return self._get_error_response("llm_error")
        except Exception as e:
            logger.exception(f"Error processing voice transcript: {e}")
            return self._get_error_response("general_error")

    async def _load_context(self, call_id: str) -> list[dict[str, str]]:
        """Load conversation context from Redis.
        
        Args:
            call_id: Bolna call ID
            
        Returns:
            List of message dicts with role and content
        """
        context_key = f"voice_context:{call_id}"
        
        try:
            context_json = await self._redis.get(context_key)
            
            if context_json:
                context = json.loads(context_json)
                messages = context.get("messages", [])
                
                # Limit context size to prevent token overflow
                if len(messages) > CONTEXT_MESSAGE_LIMIT:
                    # Keep system message + recent messages
                    system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
                    recent_messages = messages[-(CONTEXT_MESSAGE_LIMIT - 1):]
                    messages = ([system_msg] if system_msg else []) + recent_messages
                
                logger.debug(f"Loaded context: call_id={call_id}, messages={len(messages)}")
                return messages
            else:
                # First message - initialize with system prompt
                logger.info(f"Initializing new context: call_id={call_id}")
                return [
                    {
                        "role": "system",
                        "content": get_system_prompt("voice")
                    }
                ]
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            # Return fresh context on error
            return [
                {
                    "role": "system",
                    "content": get_system_prompt("voice")
                }
            ]

    async def _save_context(self, call_id: str, messages: list[dict[str, str]]) -> None:
        """Save conversation context to Redis.
        
        Args:
            call_id: Bolna call ID
            messages: List of message dicts to save
        """
        context_key = f"voice_context:{call_id}"
        
        try:
            context = {"messages": messages}
            await self._redis.setex(
                context_key,
                CONVERSATION_TTL_SECONDS,
                json.dumps(context)
            )
            logger.debug(f"Saved context: call_id={call_id}, messages={len(messages)}")
        except Exception as e:
            logger.error(f"Error saving context: {e}")
            # Don't fail the request if context save fails

    def _get_error_response(self, error_type: str) -> str:
        """Get a user-friendly error response.
        
        Args:
            error_type: Type of error
            
        Returns:
            Error message to speak to user
        """
        error_responses = {
            "llm_error": "I'm having trouble processing that right now. Let me connect you with our support team.",
            "general_error": "I apologize, but I'm experiencing technical difficulties. Please try calling again or contact us via WhatsApp.",
        }
        return error_responses.get(error_type, error_responses["general_error"])


class VoiceToolExecutor(ToolExecutor):
    """Executes tools for voice conversations.
    
    This class handles tool execution for voice calls, with the same
    logic as WhatsApp but optimized for voice responses (shorter, clearer).
    
    Security:
    - Order-related tools require phone number validation
    - Users can only access their own orders
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        user_phone: str,
    ):
        """Initialize the tool executor.
        
        Args:
            db: Async database session
            redis_client: Redis client
            user_phone: Caller's phone number (for authorization)
        """
        self._db = db
        self._redis = redis_client
        self._user_phone = user_phone
        self._chicx_client = get_chicx_client()
        self._settings = get_settings()

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Dictionary containing the tool execution result
        """
        from app.services.analytics import log_tool_call

        # Validate arguments
        is_valid, error_msg = validate_tool_arguments(tool_name, arguments)
        if not is_valid:
            logger.warning(f"Invalid tool arguments: {error_msg}")
            return {"error": error_msg}

        result = None
        success = True

        try:
            if tool_name == ToolName.SEARCH_PRODUCTS:
                result = await self._search_products(arguments)
            elif tool_name == ToolName.GET_PRODUCT_DETAILS:
                result = await self._get_product_details(arguments)
            elif tool_name == ToolName.GET_ORDER_STATUS:
                result = await self._get_order_status(arguments)
            elif tool_name == ToolName.GET_ORDER_HISTORY:
                result = await self._get_order_history(arguments)
            elif tool_name == ToolName.SEARCH_FAQ:
                result = await self._search_faq(arguments)
            elif tool_name == ToolName.TRACK_SHIPMENT:
                result = await self._track_shipment(arguments)
            else:
                logger.error(f"Unknown tool: {tool_name}")
                result = {"error": f"Unknown tool: {tool_name}"}
                success = False
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {e}")
            result = {"error": f"Failed to execute {tool_name}: {str(e)}"}
            success = False

        # Log analytics event for tool call
        await log_tool_call(
            db=self._db,
            tool_name=tool_name,
            arguments=arguments,
            result_success=success and "error" not in (result or {}),
            channel="voice",
        )

        return result or {"error": "No result"}

    # =========================================================================
    # Tool Execution Methods (copied from bolna.py with voice optimizations)
    # =========================================================================

    async def _search_products(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute product search via CHICX API."""
        try:
            result = await self._chicx_client.search_products(
                query=args.get("query", ""),
                category=args.get("category"),
                limit=3,  # Fewer results for voice
            )

            products = result.get("products", [])
            if not products:
                return {"message": "No products found matching your search."}

            # Format for speech (shorter, clearer)
            summaries = []
            for p in products[:3]:
                name = p.get("name", "Product")
                price = p.get("price", 0)
                summaries.append(f"{name} at {price} rupees")

            return {
                "products": summaries,
                "message": f"I found {len(summaries)} products: " + ", ".join(summaries),
            }

        except ChicxAPIError as e:
            logger.error(f"Product search error: {e}")
            return {"message": "Sorry, I couldn't search products right now. Please try again."}

    async def _get_product_details(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute product detail lookup via CHICX API."""
        product_id = args.get("product_id", "")

        if not product_id:
            return {"message": "Please tell me which product you'd like to know more about."}

        try:
            product = await self._chicx_client.get_product(product_id)

            if not product:
                return {"message": f"I couldn't find product {product_id}. It may no longer be available."}

            # Format for voice output
            name = product.get("title", product.get("name", "Product"))
            price = product.get("price", "")
            description = product.get("short_description", product.get("description", ""))

            voice_response = f"{name}"
            if price:
                voice_response += f" is priced at {price} rupees"
            if description:
                # Truncate description for voice
                short_desc = description[:200] if len(description) > 200 else description
                voice_response += f". {short_desc}"

            return {
                "name": name,
                "price": price,
                "description": description,
                "message": voice_response,
            }

        except ChicxAPIError as e:
            logger.error(f"Product details error: {e}")
            return {"message": "Sorry, I couldn't get product details right now. Please try again."}

    async def _get_order_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute order status lookup via CHICX API.
        
        SECURITY: Requires caller phone number for authorization.
        """
        if not self._user_phone:
            logger.error("SECURITY: Order status check without phone number")
            return {"message": "Unable to verify your identity. Please try calling again."}

        order_id = args.get("order_id", "")

        if not order_id:
            return {"message": "Please provide your order ID. You can find it in your confirmation email."}

        try:
            order = await self._chicx_client.get_order(order_id)

            if not order:
                return {"message": f"I couldn't find order {order_id}. Please check the order ID and try again."}

            # SECURITY CHECK: Verify order belongs to caller
            order_phone = order.get("phone", "")
            normalized_caller = normalize_phone(self._user_phone, for_db=True)
            normalized_order = normalize_phone(order_phone, for_db=True)

            if not normalized_caller or not normalized_order:
                logger.error(f"Phone normalization failed: caller={self._user_phone}, order={order_phone}")
                return {"message": "Unable to verify order ownership. Please contact support."}

            if normalized_caller != normalized_order:
                logger.warning(
                    f"Unauthorized order access attempt: "
                    f"caller={self._user_phone} tried order={order_id} belonging to={order_phone}"
                )
                return {"message": f"Order {order_id} not found in your account. Please check the order ID."}

            # Authorized - return order status
            status = order.get("status", "unknown")
            status_messages = {
                "placed": "Your order has been placed and is being processed.",
                "confirmed": "Your order is confirmed and will be shipped soon.",
                "shipped": "Great news! Your order has been shipped.",
                "out_for_delivery": "Your order is out for delivery today!",
                "delivered": "Your order has been delivered.",
                "cancelled": "This order has been cancelled.",
            }

            message = status_messages.get(status, f"Your order status is {status}.")

            if order.get("tracking_number"):
                message += f" Your tracking number is {order['tracking_number']}."

            return {"status": status, "message": message}

        except ChicxAPIError as e:
            logger.error(f"Order status error: {e}")
            return {"message": "Sorry, I couldn't check your order status right now. Please try again."}

    async def _get_order_history(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute order history lookup via CHICX API."""
        if not self._user_phone:
            logger.error("SECURITY: Order history check without phone number")
            return {"message": "Unable to verify your identity. Please try calling again."}

        normalized_phone = normalize_phone(self._user_phone, for_db=True)
        if not normalized_phone:
            return {"message": "Invalid phone number format. Please try calling again."}

        try:
            result = await self._chicx_client.get_order_by_phone(
                phone=normalized_phone,
                limit=args.get("limit", 3),
            )

            orders = result.get("orders", [])
            if not orders:
                return {"message": "I don't see any orders for your phone number."}

            # Format for speech
            summaries = []
            for o in orders[:3]:
                order_id = o.get("chicx_order_id", o.get("id", ""))
                status = o.get("status", "unknown")
                summaries.append(f"Order {order_id} is {status}")

            return {
                "orders": summaries,
                "message": f"You have {len(summaries)} recent orders: " + ". ".join(summaries),
            }

        except ChicxAPIError as e:
            logger.error(f"Order history error: {e}")
            return {"message": "Sorry, I couldn't get your order history right now. Please try again."}

    async def _search_faq(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute FAQ search using pgvector."""
        query = args.get("query", "")

        if not query:
            return {"message": "What would you like to know about?"}

        embedding_service = EmbeddingService(self._db)

        try:
            faqs = await embedding_service.search_faqs(
                query=query,
                limit=1,  # Just the best match for voice
            )

            if not faqs:
                return {
                    "message": "I don't have specific information about that. "
                    "For detailed help, please contact support at support@thechicx.com."
                }

            # Return the best matching answer
            best_match = faqs[0]
            return {
                "answer": best_match["answer"],
                "message": best_match["answer"],
            }

        except Exception as e:
            logger.error(f"FAQ search error: {e}")
            return {"message": "Sorry, I couldn't find that information. Please contact support@thechicx.com."}

    async def _track_shipment(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute track_shipment tool via Shiprocket API."""
        from app.services.shiprocket import get_shiprocket_client, ShiprocketAPIError

        awb_number = args.get("awb_number", "")

        if not awb_number:
            return {"message": "I need the tracking number or AWB number to track your shipment."}

        logger.info(f"Tracking shipment for voice: AWB={awb_number}")

        try:
            shiprocket = get_shiprocket_client()
            result = await shiprocket.track_by_awb(awb_number)

            if not result.get("found"):
                return {
                    "message": f"I couldn't find any shipment with tracking number {awb_number}. Please verify the number."
                }

            # Format response for voice
            status = result.get("current_status", "Unknown")
            location = result.get("current_location", "")
            edd = result.get("edd", "")
            courier = result.get("courier", "")

            voice_response = f"Your shipment is currently {status}"
            if location:
                voice_response += f" at {location}"
            if courier:
                voice_response += f" via {courier}"
            if edd:
                voice_response += f". Expected delivery is {edd}"

            return {
                "status": status,
                "location": location,
                "courier": courier,
                "expected_delivery": edd,
                "message": voice_response,
            }

        except ShiprocketAPIError as e:
            logger.error(f"Shiprocket API error: {e}")
            return {"message": "I'm unable to fetch tracking information right now. Please try again later."}
        except Exception as e:
            logger.error(f"Tracking error: {e}")
            return {"message": "Sorry, I couldn't track that shipment. Please try again."}

# Made with Bob
