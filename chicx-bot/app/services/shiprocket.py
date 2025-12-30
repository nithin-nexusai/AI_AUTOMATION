"""Shiprocket API client for shipment tracking.

This service provides live shipment tracking via Shiprocket API.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)


class ShiprocketAPIError(Exception):
    """Base exception for Shiprocket API errors."""
    pass


class ShiprocketClient:
    """Client for Shiprocket API.
    
    Provides shipment tracking functionality.
    Uses JWT authentication (token valid for 10 days).
    """
    
    BASE_URL = "https://apiv2.shiprocket.in/v1/external"
    
    def __init__(self) -> None:
        """Initialize the Shiprocket client."""
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._token_expires: datetime | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth token."""
        # Check if we need a new token
        if self._token is None or self._token_expired():
            await self._authenticate()
        
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client
    
    def _token_expired(self) -> bool:
        """Check if the auth token has expired."""
        if self._token_expires is None:
            return True
        # Refresh 1 day before expiry
        return datetime.now(timezone.utc) >= self._token_expires - timedelta(days=1)
    
    async def _authenticate(self) -> None:
        """Authenticate with Shiprocket API to get JWT token."""
        if not self._settings.shiprocket_email or not self._settings.shiprocket_password:
            raise ShiprocketAPIError("Shiprocket credentials not configured")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/auth/login",
                    json={
                        "email": self._settings.shiprocket_email,
                        "password": self._settings.shiprocket_password,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                self._token = data.get("token")
                # Token valid for 10 days
                self._token_expires = datetime.now(timezone.utc) + timedelta(days=10)
                
                logger.info("Shiprocket authentication successful")
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Shiprocket auth failed: {e.response.status_code}")
                raise ShiprocketAPIError(f"Authentication failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Shiprocket auth error: {e}")
                raise ShiprocketAPIError(f"Authentication error: {e}")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def track_by_awb(self, awb_number: str) -> dict[str, Any]:
        """Track shipment by AWB (Air Waybill) number.
        
        Args:
            awb_number: The courier AWB/tracking number
            
        Returns:
            Tracking info with status, location, and timeline
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"/courier/track/awb/{awb_number}")
            response.raise_for_status()
            data = response.json()
            
            # Parse tracking data
            tracking_data = data.get("tracking_data", {})
            shipment_track = tracking_data.get("shipment_track", [])
            
            if not shipment_track:
                return {
                    "found": False,
                    "awb": awb_number,
                    "message": "No tracking information found for this AWB",
                }
            
            # Get latest status
            latest = shipment_track[0] if shipment_track else {}
            
            return {
                "found": True,
                "awb": awb_number,
                "current_status": latest.get("current_status", "Unknown"),
                "current_location": latest.get("current_status_location", ""),
                "origin": latest.get("origin", ""),
                "destination": latest.get("destination", ""),
                "courier": latest.get("courier_name", ""),
                "edd": latest.get("edd", ""),  # Expected delivery date
                "last_update": latest.get("current_status_time", ""),
                "track_url": f"https://shiprocket.co/tracking/{awb_number}",
                "timeline": [
                    {
                        "status": event.get("activity", ""),
                        "location": event.get("location", ""),
                        "time": event.get("date", ""),
                    }
                    for event in tracking_data.get("shipment_track_activities", [])[:5]
                ],
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "found": False,
                    "awb": awb_number,
                    "message": "AWB number not found",
                }
            logger.error(f"Shiprocket API error: {e.response.status_code}")
            raise ShiprocketAPIError(f"Tracking failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Shiprocket request error: {e}")
            raise ShiprocketAPIError(f"Connection error: {e}")
    
    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def track_by_order_id(self, order_id: str) -> dict[str, Any]:
        """Track shipment by Shiprocket order ID.
        
        Args:
            order_id: The Shiprocket order ID
            
        Returns:
            Tracking info with status and timeline
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"/courier/track", params={"order_id": order_id})
            response.raise_for_status()
            data = response.json()
            
            if not data.get("tracking_data"):
                return {
                    "found": False,
                    "order_id": order_id,
                    "message": "No tracking information found",
                }
            
            tracking = data["tracking_data"]
            
            return {
                "found": True,
                "order_id": order_id,
                "awb": tracking.get("awb_code", ""),
                "current_status": tracking.get("current_status", "Unknown"),
                "courier": tracking.get("courier_name", ""),
                "edd": tracking.get("edd", ""),
                "track_url": f"https://shiprocket.co/tracking/{tracking.get('awb_code', '')}",
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "found": False,
                    "order_id": order_id,
                    "message": "Order not found in Shiprocket",
                }
            raise ShiprocketAPIError(f"Tracking failed: {e.response.status_code}")


# Singleton instance
_client_instance: ShiprocketClient | None = None


def get_shiprocket_client() -> ShiprocketClient:
    """Get or create the global Shiprocket client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ShiprocketClient()
    return _client_instance


async def shutdown_shiprocket_client() -> None:
    """Shutdown the global Shiprocket client."""
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None
