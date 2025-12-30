"""Bolna API client for outbound calls.

This service handles:
- Making outbound calls via Bolna platform
- Injecting order context into conversations
"""

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)


class BolnaAPIError(Exception):
    """Base exception for Bolna API errors."""
    pass


class BolnaClient:
    """Client for Bolna Platform API.
    
    Handles outbound call initiation for order confirmations.
    """
    
    def __init__(self) -> None:
        """Initialize the Bolna client."""
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            if not self._settings.bolna_api_key:
                raise BolnaAPIError("BOLNA_API_KEY not configured")
            
            self._client = httpx.AsyncClient(
                base_url=self._settings.bolna_base_url,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._settings.bolna_api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def make_outbound_call(
        self,
        phone: str,
        agent_id: str,
        context: dict[str, Any] | None = None,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        """Initiate an outbound call via Bolna.
        
        Args:
            phone: Phone number to call (with country code)
            agent_id: Bolna agent ID to use for the call
            context: Optional context to inject (order details, customer name, etc.)
            webhook_url: Optional custom webhook URL for call events
            
        Returns:
            Dict with call_id and status
        """
        client = await self._get_client()
        
        # Normalize phone number
        phone = phone.lstrip("+").replace(" ", "").replace("-", "")
        if len(phone) == 10:
            phone = "91" + phone  # Add India country code
        
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "recipient_phone_number": phone,
        }
        
        # Add context for the conversation
        if context:
            payload["context"] = context
            # Build dynamic prompt injection
            if "order_id" in context:
                payload["dynamic_variables"] = {
                    "order_id": context.get("order_id", ""),
                    "customer_name": context.get("customer_name", "customer"),
                    "items_summary": context.get("items_summary", "your order"),
                    "total_amount": str(context.get("total_amount", "")),
                }
        
        # Custom webhook for call completion
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        logger.info(f"Initiating outbound call to {phone} with agent {agent_id}")
        
        try:
            response = await client.post("/call", json=payload)
            response.raise_for_status()
            data = response.json()
            
            call_id = data.get("call_id") or data.get("id")
            logger.info(f"Outbound call initiated: {call_id}")
            
            return {
                "success": True,
                "call_id": call_id,
                "phone": phone,
                "status": data.get("status", "initiated"),
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Bolna API error: {e.response.status_code} - {e.response.text}")
            raise BolnaAPIError(f"Failed to initiate call: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Bolna connection error: {e}")
            raise BolnaAPIError(f"Connection error: {e}")
    
    async def get_call_status(self, call_id: str) -> dict[str, Any]:
        """Get status of an ongoing or completed call.
        
        Args:
            call_id: Bolna call ID
            
        Returns:
            Call status and details
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"/call/{call_id}")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get call status: {e.response.status_code}")
            raise BolnaAPIError(f"Failed to get call status: {e.response.status_code}")


# Singleton instance
_client_instance: BolnaClient | None = None


def get_bolna_client() -> BolnaClient:
    """Get or create the global Bolna client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = BolnaClient()
    return _client_instance


async def shutdown_bolna_client() -> None:
    """Shutdown the global Bolna client."""
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None
