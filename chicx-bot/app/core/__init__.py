"""Core utilities for LLM, tools, and prompts.

This module provides the core AI/ML infrastructure for the CHICX WhatsApp bot:
- DeepSeek LLM client for natural language processing
- Tool definitions for function calling
- System prompts for bot behavior
"""

from app.core.llm import (
    DeepSeekClient,
    ToolExecutor,
    LLMError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
    get_llm_client,
    shutdown_llm_client,
)
from app.core.tools import (
    TOOL_DEFINITIONS,
    ToolName,
    get_tool_definitions,
    get_tool_by_name,
    get_tool_names,
    validate_tool_arguments,
    TOOL_RESPONSE_SCHEMAS,
)
from app.core.prompts import (
    WHATSAPP_SYSTEM_PROMPT,
    VOICE_SYSTEM_PROMPT,
    ERROR_RESPONSES,
    ORDER_STATUS_DESCRIPTIONS,
    QUICK_REPLIES,
    get_system_prompt,
    get_error_response,
    get_order_status_description,
    get_quick_replies,
    format_product_message,
    format_order_summary,
    get_notification_template,
)

__all__ = [
    # LLM Client
    "DeepSeekClient",
    "ToolExecutor",
    "LLMError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMResponseError",
    "get_llm_client",
    "shutdown_llm_client",
    # Tools
    "TOOL_DEFINITIONS",
    "ToolName",
    "get_tool_definitions",
    "get_tool_by_name",
    "get_tool_names",
    "validate_tool_arguments",
    "TOOL_RESPONSE_SCHEMAS",
    # Prompts
    "WHATSAPP_SYSTEM_PROMPT",
    "VOICE_SYSTEM_PROMPT",
    "ERROR_RESPONSES",
    "ORDER_STATUS_DESCRIPTIONS",
    "QUICK_REPLIES",
    "get_system_prompt",
    "get_error_response",
    "get_order_status_description",
    "get_quick_replies",
    "format_product_message",
    "format_order_summary",
    "get_notification_template",
]
