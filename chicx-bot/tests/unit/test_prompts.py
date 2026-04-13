"""Unit tests for prompts module."""

import pytest
from app.core.prompts import (
    get_system_prompt,
    get_error_response,
    get_order_status_description,
    WHATSAPP_SYSTEM_PROMPT,
)


@pytest.mark.unit
class TestSystemPrompts:
    """Test system prompt functions."""

    def test_get_system_prompt_whatsapp(self):
        """Test getting WhatsApp system prompt."""
        prompt = get_system_prompt("whatsapp")
        assert prompt == WHATSAPP_SYSTEM_PROMPT
        assert "CHICX Assistant" in prompt
        assert "multilingual" in prompt.lower()

    def test_get_system_prompt_voice(self):
        """Test that voice channel returns WhatsApp prompt (voice prompts in Bolna)."""
        prompt = get_system_prompt("voice")
        assert prompt == WHATSAPP_SYSTEM_PROMPT
        assert "CHICX Assistant" in prompt

    def test_get_system_prompt_default(self):
        """Test default system prompt."""
        prompt = get_system_prompt()
        assert prompt == WHATSAPP_SYSTEM_PROMPT


@pytest.mark.unit
class TestErrorResponses:
    """Test error response functions."""

    def test_get_error_response_english(self):
        """Test English error responses."""
        response = get_error_response("product_not_found", "en")
        assert "couldn't find" in response.lower()
        assert len(response) > 0

    def test_get_error_response_tamil(self):
        """Test Tamil error responses."""
        response = get_error_response("product_not_found", "ta")
        assert len(response) > 0

    def test_get_error_response_tanglish(self):
        """Test Tanglish error responses."""
        response = get_error_response("product_not_found", "tanglish")
        assert len(response) > 0

    def test_get_error_response_invalid_type(self):
        """Test fallback for invalid error type."""
        response = get_error_response("invalid_error_type", "en")
        assert "trouble" in response.lower()

    def test_get_error_response_invalid_language(self):
        """Test fallback for invalid language."""
        response = get_error_response("product_not_found", "invalid_lang")
        assert len(response) > 0  # Should fallback to English


@pytest.mark.unit
class TestOrderStatusDescriptions:
    """Test order status description functions."""

    def test_get_order_status_placed(self):
        """Test 'placed' status description."""
        desc = get_order_status_description("placed", "en")
        assert "placed" in desc.lower()
        assert "successfully" in desc.lower()

    def test_get_order_status_shipped(self):
        """Test 'shipped' status description."""
        desc = get_order_status_description("shipped", "en")
        assert "shipped" in desc.lower() or "way" in desc.lower()

    def test_get_order_status_delivered(self):
        """Test 'delivered' status description."""
        desc = get_order_status_description("delivered", "en")
        assert "delivered" in desc.lower()

    def test_get_order_status_tamil(self):
        """Test Tamil status descriptions."""
        desc = get_order_status_description("shipped", "ta")
        assert len(desc) > 0

    def test_get_order_status_tanglish(self):
        """Test Tanglish status descriptions."""
        desc = get_order_status_description("shipped", "tanglish")
        assert len(desc) > 0

    def test_get_order_status_invalid(self):
        """Test invalid status fallback."""
        desc = get_order_status_description("invalid_status", "en")
        assert "Order status" in desc
        assert "invalid_status" in desc

    def test_get_order_status_case_insensitive(self):
        """Test case insensitive status matching."""
        desc1 = get_order_status_description("SHIPPED", "en")
        desc2 = get_order_status_description("shipped", "en")
        assert desc1 == desc2


