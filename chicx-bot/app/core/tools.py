"""LLM tool definitions for CHICX WhatsApp bot function calling.

This module defines the 5 core tools that the LLM can use to interact with
the CHICX platform:
1. search_products - Search the product catalog
2. get_product_details - Get details of a specific product
3. get_order_status - Track an order by ID
4. get_order_history - List a user's past orders
5. search_faq - Semantic search for FAQs using pgvector

Tools are defined in OpenAI function calling format.
"""

from typing import Any


# Tool definitions in OpenAI function calling format
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search the CHICX product catalog for women's fashion items. "
                "Use this to find products matching a query, filter by category, "
                "or filter by price range. Returns a list of matching products with "
                "basic details. The bot is read-only, so direct users to the website "
                "to make purchases."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query to match against product names and descriptions. "
                            "Example: 'red saree', 'cotton kurti', 'party dress'"
                        ),
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            "Filter by product category. Common categories include: "
                            "sarees, kurtis, dresses, tops, bottoms, ethnic-wear, western-wear, "
                            "accessories, footwear"
                        ),
                        "enum": [
                            "sarees",
                            "kurtis",
                            "dresses",
                            "tops",
                            "bottoms",
                            "ethnic-wear",
                            "western-wear",
                            "accessories",
                            "footwear",
                            "lehengas",
                            "salwar-suits",
                        ],
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price filter in INR. Example: 500",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price filter in INR. Example: 2000",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Default is 5, max is 10.",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": (
                "Get detailed information about a specific product by its ID. "
                "Use this when the user wants to know more about a particular product "
                "they saw in search results. Returns full product details including "
                "description, price, available variants (sizes/colors), and the "
                "product URL where they can purchase on the CHICX website."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": (
                            "The unique product identifier (CHICX product ID or UUID). "
                            "This is returned in search results."
                        ),
                    },
                },
                "required": ["product_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": (
                "Get the current status and tracking information for a specific order. "
                "Use this when the user wants to track their order or know when it will "
                "be delivered. Returns order status, tracking number, shipping details, "
                "and delivery timeline. The user must provide their order ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": (
                            "The CHICX order ID to look up. This is provided to customers "
                            "in their order confirmation email/SMS. Format is typically "
                            "alphanumeric like 'CHX123456' or a UUID."
                        ),
                    },
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_history",
            "description": (
                "Get a list of the user's past orders. Use this when the user wants "
                "to see their order history or find a specific past order. Returns a "
                "summary of recent orders including order IDs, dates, items, amounts, "
                "and current status. The user is identified by their phone number "
                "from the WhatsApp conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of orders to return. Default is 5.",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "status_filter": {
                        "type": "string",
                        "description": "Optional filter for order status.",
                        "enum": [
                            "placed",
                            "confirmed",
                            "shipped",
                            "out_for_delivery",
                            "delivered",
                            "cancelled",
                        ],
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": (
                "Search the FAQ knowledge base for answers to customer questions. "
                "Use this for questions about shipping, returns, payment methods, "
                "sizing, care instructions, policies, and general customer support. "
                "Uses semantic search powered by pgvector to find the most relevant "
                "FAQ entries even if the exact keywords don't match."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The user's question or search query. Can be a natural "
                            "language question like 'How do I return an item?' or "
                            "keywords like 'return policy refund'"
                        ),
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category to narrow down FAQ search.",
                        "enum": [
                            "shipping",
                            "returns",
                            "payment",
                            "sizing",
                            "care",
                            "account",
                            "orders",
                            "general",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of FAQ entries to return. Default is 3.",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get all tool definitions for LLM function calling.

    Returns:
        List of tool definitions in OpenAI function calling format.
    """
    return TOOL_DEFINITIONS.copy()


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a specific tool definition by name.

    Args:
        name: The name of the tool to retrieve.

    Returns:
        The tool definition dict, or None if not found.
    """
    for tool in TOOL_DEFINITIONS:
        if tool["function"]["name"] == name:
            return tool.copy()
    return None


def get_tool_names() -> list[str]:
    """Get a list of all available tool names.

    Returns:
        List of tool names as strings.
    """
    return [tool["function"]["name"] for tool in TOOL_DEFINITIONS]


# Tool name constants for type-safe usage
class ToolName:
    """Constants for tool names to avoid string typos."""

    SEARCH_PRODUCTS = "search_products"
    GET_PRODUCT_DETAILS = "get_product_details"
    GET_ORDER_STATUS = "get_order_status"
    GET_ORDER_HISTORY = "get_order_history"
    SEARCH_FAQ = "search_faq"


# Mapping of tool names to their required parameters for validation
TOOL_REQUIRED_PARAMS: dict[str, list[str]] = {
    ToolName.SEARCH_PRODUCTS: [],
    ToolName.GET_PRODUCT_DETAILS: ["product_id"],
    ToolName.GET_ORDER_STATUS: ["order_id"],
    ToolName.GET_ORDER_HISTORY: [],
    ToolName.SEARCH_FAQ: ["query"],
}


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate that required arguments are provided for a tool.

    Args:
        tool_name: Name of the tool being called.
        arguments: Dictionary of arguments provided.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, returns (True, None).
        If invalid, returns (False, error_message).
    """
    if tool_name not in TOOL_REQUIRED_PARAMS:
        return False, f"Unknown tool: {tool_name}"

    required = TOOL_REQUIRED_PARAMS[tool_name]
    missing = [param for param in required if param not in arguments or arguments[param] is None]

    if missing:
        return False, f"Missing required parameters for {tool_name}: {', '.join(missing)}"

    return True, None


# Response schemas for documentation purposes
TOOL_RESPONSE_SCHEMAS: dict[str, dict[str, Any]] = {
    ToolName.SEARCH_PRODUCTS: {
        "type": "object",
        "properties": {
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "chicx_product_id": {"type": "string"},
                        "name": {"type": "string"},
                        "category": {"type": "string"},
                        "price": {"type": "number"},
                        "image_url": {"type": "string"},
                        "product_url": {"type": "string"},
                    },
                },
            },
            "total_count": {"type": "integer"},
            "has_more": {"type": "boolean"},
        },
    },
    ToolName.GET_PRODUCT_DETAILS: {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "chicx_product_id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "category": {"type": "string"},
            "price": {"type": "number"},
            "image_url": {"type": "string"},
            "product_url": {"type": "string"},
            "variants": {
                "type": "object",
                "properties": {
                    "sizes": {"type": "array", "items": {"type": "string"}},
                    "colors": {"type": "array", "items": {"type": "string"}},
                },
            },
            "is_active": {"type": "boolean"},
        },
    },
    ToolName.GET_ORDER_STATUS: {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "chicx_order_id": {"type": "string"},
            "status": {"type": "string"},
            "status_description": {"type": "string"},
            "placed_at": {"type": "string", "format": "date-time"},
            "total_amount": {"type": "number"},
            "item_count": {"type": "integer"},
            "tracking_number": {"type": "string"},
            "estimated_delivery": {"type": "string"},
            "shipping_address": {"type": "object"},
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "description": {"type": "string"},
                    },
                },
            },
        },
    },
    ToolName.GET_ORDER_HISTORY: {
        "type": "object",
        "properties": {
            "orders": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "chicx_order_id": {"type": "string"},
                        "status": {"type": "string"},
                        "placed_at": {"type": "string", "format": "date-time"},
                        "total_amount": {"type": "number"},
                        "item_count": {"type": "integer"},
                        "items_summary": {"type": "string"},
                    },
                },
            },
            "total_orders": {"type": "integer"},
        },
    },
    ToolName.SEARCH_FAQ: {
        "type": "object",
        "properties": {
            "faqs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "category": {"type": "string"},
                        "relevance_score": {"type": "number"},
                    },
                },
            },
        },
    },
}
