"""End-to-end tests for complete WhatsApp conversation flows."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.whatsapp
@pytest.mark.slow
class TestWhatsAppConversationFlow:
    """Test complete WhatsApp conversation flows."""

    @patch("app.services.whatsapp.WhatsAppService.send_text_message")
    @patch("app.core.llm.OpenRouterClient.chat_with_tools")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_product_search_flow(
        self,
        mock_verify,
        mock_llm,
        mock_send,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test complete product search conversation flow."""
        # Setup mocks
        mock_verify.return_value = True
        mock_llm.return_value = {
            "content": "Here are some beautiful red sarees I found for you!",
            "iterations": 1,
            "tool_calls_made": [
                {
                    "name": "search_products",
                    "arguments": {"query": "red saree", "limit": 5},
                    "result": {"products": []},
                }
            ],
        }
        mock_send.return_value = AsyncMock()
        
        # User sends message
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("app.services.whatsapp.WhatsAppService.send_text_message")
    @patch("app.core.llm.OpenRouterClient.chat_with_tools")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_order_tracking_flow(
        self,
        mock_verify,
        mock_llm,
        mock_send,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test complete order tracking conversation flow."""
        # Modify message to ask about order
        sample_whatsapp_message["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "Track my order CHX12345"
        
        # Setup mocks
        mock_verify.return_value = True
        mock_llm.return_value = {
            "content": "Your order CHX12345 has been shipped and is on its way!",
            "iterations": 1,
            "tool_calls_made": [
                {
                    "name": "get_order_status",
                    "arguments": {"order_id": "CHX12345"},
                    "result": {"status": "shipped"},
                }
            ],
        }
        mock_send.return_value = AsyncMock()
        
        # User sends message
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("app.services.whatsapp.WhatsAppService.send_text_message")
    @patch("app.core.llm.OpenRouterClient.chat_with_tools")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_faq_search_flow(
        self,
        mock_verify,
        mock_llm,
        mock_send,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test FAQ search conversation flow."""
        # Modify message to ask FAQ
        sample_whatsapp_message["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "What is your return policy?"
        
        # Setup mocks
        mock_verify.return_value = True
        mock_llm.return_value = {
            "content": "We offer 7-day returns on all products. Items must be unused and in original packaging.",
            "iterations": 1,
            "tool_calls_made": [
                {
                    "name": "search_faq",
                    "arguments": {"query": "return policy"},
                    "result": {"faqs": [{"answer": "7-day returns"}]},
                }
            ],
        }
        mock_send.return_value = AsyncMock()
        
        # User sends message
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("app.services.whatsapp.WhatsAppService.send_text_message")
    @patch("app.core.llm.OpenRouterClient.chat_with_tools")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_multilingual_conversation(
        self,
        mock_verify,
        mock_llm,
        mock_send,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test multilingual conversation (Tanglish)."""
        # Modify message to Tanglish
        sample_whatsapp_message["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "Saree venum"
        
        # Setup mocks
        mock_verify.return_value = True
        mock_llm.return_value = {
            "content": "Sure! Enna type saree venum? Silk, cotton, or designer?",
            "iterations": 1,
            "tool_calls_made": [],
        }
        mock_send.return_value = AsyncMock()
        
        # User sends message
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.e2e
@pytest.mark.whatsapp
@pytest.mark.slow
class TestErrorHandlingFlow:
    """Test error handling in complete flows."""

    @patch("app.services.whatsapp.WhatsAppService.send_text_message")
    @patch("app.core.llm.OpenRouterClient.chat_with_tools")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_llm_timeout_handling(
        self,
        mock_verify,
        mock_llm,
        mock_send,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test handling of LLM timeout."""
        import asyncio
        
        # Setup mocks
        mock_verify.return_value = True
        mock_llm.side_effect = asyncio.TimeoutError()
        mock_send.return_value = AsyncMock()
        
        # User sends message
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        # Should still return ok even if LLM times out

    @patch("app.services.whatsapp.WhatsAppService.send_text_message")
    @patch("app.core.llm.OpenRouterClient.chat_with_tools")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_message_send_failure_handling(
        self,
        mock_verify,
        mock_llm,
        mock_send,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test handling of message send failure."""
        # Setup mocks
        mock_verify.return_value = True
        mock_llm.return_value = {
            "content": "Test response",
            "iterations": 1,
            "tool_calls_made": [],
        }
        mock_send.side_effect = Exception("Network error")
        
        # User sends message
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        # Should still return ok even if send fails


@pytest.mark.e2e
@pytest.mark.slow
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_main_health_endpoint(self, test_client: TestClient):
        """Test main health endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_webhook_health_endpoint(self, test_client: TestClient):
        """Test webhook health endpoint."""
        response = test_client.get("/webhooks/whatsapp/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "whatsapp-webhook"

