"""Unit tests for tools module."""

import pytest
from app.core.tools import (
    get_tool_definitions,
    validate_tool_arguments,
    ToolName,
)


@pytest.mark.unit
class TestToolDefinitions:
    """Test tool definition functions."""

    def test_get_tool_definitions_returns_list(self):
        """Test that get_tool_definitions returns a list."""
        tools = get_tool_definitions()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_get_tool_definitions_structure(self):
        """Test tool definition structure."""
        tools = get_tool_definitions()
        
        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_all_tools_present(self):
        """Test that all expected tools are defined."""
        tools = get_tool_definitions()
        tool_names = [tool["function"]["name"] for tool in tools]
        
        expected_tools = [
            "search_products",
            "get_product_details",
            "get_order_status",
            "get_order_history",
            "search_faq",
            "track_shipment",
        ]
        
        for expected in expected_tools:
            assert expected in tool_names

    def test_search_products_tool(self):
        """Test search_products tool definition."""
        tools = get_tool_definitions()
        search_tool = next(
            t for t in tools if t["function"]["name"] == "search_products"
        )
        
        params = search_tool["function"]["parameters"]["properties"]
        assert "query" in params
        assert "category" in params
        assert "min_price" in params
        assert "max_price" in params
        assert "limit" in params

    def test_get_product_details_tool(self):
        """Test get_product_details tool definition."""
        tools = get_tool_definitions()
        details_tool = next(
            t for t in tools if t["function"]["name"] == "get_product_details"
        )
        
        params = details_tool["function"]["parameters"]["properties"]
        assert "product_id" in params
        assert details_tool["function"]["parameters"]["required"] == ["product_id"]


@pytest.mark.unit
class TestToolValidation:
    """Test tool argument validation."""

    def test_validate_search_products_valid(self):
        """Test valid search_products arguments."""
        args = {
            "query": "red saree",
            "category": "sarees",
            "min_price": 500,
            "max_price": 2000,
            "limit": 5,
        }
        
        is_valid, error = validate_tool_arguments(ToolName.SEARCH_PRODUCTS, args)
        assert is_valid is True
        assert error is None

    def test_validate_search_products_minimal(self):
        """Test search_products with minimal arguments."""
        args = {}
        
        is_valid, error = validate_tool_arguments(ToolName.SEARCH_PRODUCTS, args)
        assert is_valid is True

    def test_validate_get_product_details_valid(self):
        """Test valid get_product_details arguments."""
        args = {"product_id": "prod_123"}
        
        is_valid, error = validate_tool_arguments(ToolName.GET_PRODUCT_DETAILS, args)
        assert is_valid is True

    def test_validate_get_product_details_missing_id(self):
        """Test get_product_details without required product_id."""
        args = {}
        
        is_valid, error = validate_tool_arguments(ToolName.GET_PRODUCT_DETAILS, args)
        assert is_valid is False
        assert error is not None
        assert "product_id" in error.lower()

    def test_validate_get_order_status_valid(self):
        """Test valid get_order_status arguments."""
        args = {"order_id": "CHX12345"}
        
        is_valid, error = validate_tool_arguments(ToolName.GET_ORDER_STATUS, args)
        assert is_valid is True

    def test_validate_invalid_tool_name(self):
        """Test validation with invalid tool name."""
        args = {"query": "test"}
        
        is_valid, error = validate_tool_arguments("invalid_tool", args)
        assert is_valid is False
        assert error is not None


@pytest.mark.unit
class TestToolName:
    """Test ToolName enum."""

    def test_tool_name_values(self):
        """Test ToolName enum values."""
        assert ToolName.SEARCH_PRODUCTS == "search_products"
        assert ToolName.GET_PRODUCT_DETAILS == "get_product_details"
        assert ToolName.GET_ORDER_STATUS == "get_order_status"
        assert ToolName.GET_ORDER_HISTORY == "get_order_history"
        assert ToolName.SEARCH_FAQ == "search_faq"
        assert ToolName.TRACK_SHIPMENT == "track_shipment"

    def test_tool_name_membership(self):
        """Test ToolName enum membership."""
        # ToolName is a string literal type, not an enum, so we check the constant values
        assert ToolName.SEARCH_PRODUCTS == "search_products"
        assert ToolName.GET_PRODUCT_DETAILS == "get_product_details"
