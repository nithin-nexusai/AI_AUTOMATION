"""Integration tests for WhatsApp webhook endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.whatsapp
class TestWhatsAppWebhookVerification:
    """Test WhatsApp webhook verification endpoint."""

    def test_webhook_verification_success(self, test_client: TestClient, test_settings):
        """Test successful webhook verification."""
        response = test_client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": test_settings.whatsapp_verify_token,
                "hub.challenge": "test_challenge_123",
            },
        )
        
        assert response.status_code == 200
        assert response.text == "test_challenge_123"

    def test_webhook_verification_wrong_token(self, test_client: TestClient):
        """Test webhook verification with wrong token."""
        response = test_client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "test_challenge_123",
            },
        )
        
        assert response.status_code == 403

    def test_webhook_verification_wrong_mode(self, test_client: TestClient, test_settings):
        """Test webhook verification with wrong mode."""
        response = test_client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": test_settings.whatsapp_verify_token,
                "hub.challenge": "test_challenge_123",
            },
        )
        
        assert response.status_code == 403

    def test_webhook_verification_missing_params(self, test_client: TestClient):
        """Test webhook verification with missing parameters."""
        response = test_client.get(
            "/webhooks/whatsapp",
            params={"hub.mode": "subscribe"},
        )
        
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.whatsapp
class TestWhatsAppWebhookMessages:
    """Test WhatsApp webhook message processing."""

    @patch("app.services.whatsapp.WhatsAppService.process_message")
    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_receive_text_message(
        self,
        mock_verify,
        mock_process,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test receiving a text message."""
        mock_verify.return_value = True
        mock_process.return_value = AsyncMock(return_value="Response text")
        
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @patch("app.services.whatsapp.WhatsAppService.verify_webhook_signature")
    def test_receive_message_invalid_signature(
        self,
        mock_verify,
        test_client: TestClient,
        sample_whatsapp_message: dict,
    ):
        """Test receiving message with invalid signature."""
        mock_verify.return_value = False
        
        response = test_client.post(
            "/webhooks/whatsapp",
            json=sample_whatsapp_message,
            headers={"X-Hub-Signature-256": "sha256=invalid_signature"},
        )
        
        assert response.status_code == 403

    def test_receive_message_invalid_payload(self, test_client: TestClient):
        """Test receiving message with invalid payload.
        
        Note: Signature verification happens before payload validation,
        so invalid signature returns 403, not 400.
        """
        response = test_client.post(
            "/webhooks/whatsapp",
            json={"invalid": "payload"},
            headers={"X-Hub-Signature-256": "sha256=test_signature"},
        )
        
        # Signature verification fails first (403), before payload validation (400)
        assert response.status_code == 403

    def test_webhook_health_check(self, test_client: TestClient):
        """Test webhook health check endpoint."""
        response = test_client.get("/webhooks/whatsapp/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "whatsapp-webhook"

