"""CHICX Backend API client.

This service calls the CHICX backend APIs directly for:
- Product search and details
- Order status and history

FAQs are still stored locally with pgvector for semantic search.
"""

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)


class ChicxAPIError(Exception):
    """Base exception for CHICX API errors."""
    pass


class ChicxAPIClient:
    """Client for CHICX Backend APIs.

    Calls the main CHICX e-commerce backend for real-time data.
    """

    def __init__(self) -> None:
        """Initialize the API client."""
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

        if not self._settings.chicx_api_base_url:
            logger.warning("CHICX_API_BASE_URL not configured")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._settings.chicx_api_base_url,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._settings.chicx_api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================================================
    # Product APIs
    # =========================================================================

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def search_products(
        self,
        query: str | None = None,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Search products from CHICX backend.

        Args:
            query: Search query text
            category: Category filter
            min_price: Minimum price filter
            max_price: Maximum price filter
            limit: Max results to return

        Returns:
            Dict with products list and metadata
        """
        client = await self._get_client()

        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price

        try:
            # Adjust endpoint based on actual CHICX API spec
            response = await client.get("/api/products/search", params=params)
            response.raise_for_status()
            data = response.json()

            logger.info(f"CHICX product search: query={query}, results={len(data.get('products', []))}")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"CHICX API error: {e.response.status_code} - {e.response.text}")
            raise ChicxAPIError(f"Failed to search products: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_product(self, product_id: str) -> dict[str, Any] | None:
        """Get product details from CHICX backend.

        Args:
            product_id: CHICX product ID

        Returns:
            Product details dict or None if not found
        """
        client = await self._get_client()

        try:
            # Adjust endpoint based on actual CHICX API spec
            response = await client.get(f"/api/products/{product_id}")

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get product: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")

    # =========================================================================
    # Order APIs
    # =========================================================================

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        """Get order details from CHICX backend.

        Args:
            order_id: CHICX order ID

        Returns:
            Order details dict or None if not found
        """
        client = await self._get_client()

        try:
            # Adjust endpoint based on actual CHICX API spec
            response = await client.get(f"/api/orders/{order_id}")

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get order: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_order_by_phone(
        self,
        phone: str,
        limit: int = 5,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Get orders for a customer by phone number.

        Args:
            phone: Customer phone number
            limit: Max orders to return
            status: Optional status filter

        Returns:
            Dict with orders list
        """
        client = await self._get_client()

        # Normalize phone
        phone = phone.lstrip("+")

        params: dict[str, Any] = {
            "phone": phone,
            "limit": limit,
        }
        if status:
            params["status"] = status

        try:
            # Adjust endpoint based on actual CHICX API spec
            response = await client.get("/api/orders", params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get orders: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")


# Singleton instance
_client_instance: ChicxAPIClient | None = None


def get_chicx_client() -> ChicxAPIClient:
    """Get or create the global CHICX API client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ChicxAPIClient()
    return _client_instance


async def shutdown_chicx_client() -> None:
    """Shutdown the global CHICX API client."""
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None
