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
        limit: int = 10,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search products from CHICX backend.

        Endpoint: /api/get_products.php?search=sofa
        
        Response:
        {
            "status": true,
            "page": 1,
            "limit": 10,
            "total_records": 2,
            "total_pages": 1,
            "data": [
                {
                    "id": "5",
                    "sku": "SKU-1001",
                    "category": "Furniture",
                    "title": "Luxury Blue Sofa",
                    "price": "45999.00",
                    ...
                }
            ]
        }

        Args:
            query: Search query text
            category: Category filter
            min_price: Minimum price filter
            max_price: Maximum price filter
            limit: Max results to return (default 10)
            page: Page number for pagination

        Returns:
            Dict with products list and metadata
        """
        client = await self._get_client()

        params: dict[str, Any] = {
            "limit": limit,
            "page": page,
        }
        if query:
            params["search"] = query  # API uses 'search' parameter
        if category:
            params["category"] = category
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price

        try:
            response = await client.get("/api/get_products.php", params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                logger.warning(f"Product search returned no results: {query}")
                return {"products": [], "total_count": 0}

            # Map API response to our expected format
            products = data.get("data", [])
            logger.info(f"CHICX product search: query={query}, results={len(products)}")
            
            return {
                "products": products,
                "total_count": data.get("total_records", len(products)),
                "page": data.get("page", page),
                "total_pages": data.get("total_pages", 1),
            }

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

        Uses /api/get_products.php?search={id} to find product by ID.
        
        Note: No dedicated product detail endpoint in API docs.
        Falls back to search by product ID/SKU.

        Args:
            product_id: CHICX product ID or SKU

        Returns:
            Product details dict or None if not found
        """
        client = await self._get_client()

        try:
            # Search by product ID/SKU
            response = await client.get(
                "/api/get_products.php",
                params={"search": product_id}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("status"):
                return None
            
            products = data.get("data", [])
            
            # Find exact match by ID or SKU
            for product in products:
                if str(product.get("id")) == str(product_id) or product.get("sku") == product_id:
                    return product
            
            # Return first result if no exact match
            return products[0] if products else None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get product: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")

    # =========================================================================
    # Order APIs - Based on CHICX Backend Documentation
    # =========================================================================

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        """Get order details from CHICX backend.

        Endpoint: /api/get_order.php?order_id=ORD123
        
        Response includes:
        - order_id, order_date, order_status
        - payment details (method, id, status, amount)
        - items list with product details
        - summary with grand_total

        Args:
            order_id: CHICX order ID (e.g., "ORD123456")

        Returns:
            Order details dict with 'order' key, or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(
                "/api/get_order.php",
                params={"order_id": order_id}
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()
            
            # API returns {status: true/false, order: {...}}
            if not data.get("status"):
                logger.warning(f"Order not found: {order_id}")
                return None
                
            return data.get("order")

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
    async def get_order_status(self, order_id: str) -> dict[str, Any] | None:
        """Get order status from CHICX backend.

        Endpoint: /api/order_status.php?order_id=ORD123456
        
        Response:
        {
            "status": true,
            "order_id": "ORD123456",
            "order_status": "Delivered",
            "payment_status": "Paid",
            "last_updated": "2025-12-17 11:30:00"
        }

        Args:
            order_id: CHICX order ID

        Returns:
            Order status dict or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(
                "/api/order_status.php",
                params={"order_id": order_id}
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()
            
            if not data.get("status"):
                return None
                
            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get order status: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_orders_by_user_id(
        self,
        user_id: int,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Get orders for a customer by user ID.

        Endpoint: /api/my_orders.php?user_id=5
        
        Response:
        {
            "status": true,
            "total_orders": 2,
            "orders": [{...}, {...}]
        }

        Args:
            user_id: CHICX user ID (from their database)
            limit: Max orders to return

        Returns:
            Dict with orders list
        """
        client = await self._get_client()

        params: dict[str, Any] = {
            "user_id": user_id,
        }

        try:
            response = await client.get("/api/my_orders.php", params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("status"):
                return {"orders": [], "total_orders": 0}
            
            # Apply limit locally if needed
            orders = data.get("orders", [])[:limit]
            return {
                "orders": orders,
                "total_orders": data.get("total_orders", len(orders)),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get orders: {e.response.status_code}")
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

        Endpoint: /api/get_order.php?phone=9876543210
        
        Response:
        {
            "status": true,
            "order": {
                "id": 15,
                "order_id": "ORD123456",
                "user_id": 5,
                "order_date": "2025-12-17 11:30:00",
                "order_status": "Delivered",
                "payment": {...},
                "items": [...],
                "summary": {...}
            }
        }

        Args:
            phone: Customer phone number
            limit: Max orders to return
            status: Optional status filter (not yet supported by backend)

        Returns:
            Dict with orders list
        """
        client = await self._get_client()

        # Normalize phone
        phone = phone.lstrip("+")

        try:
            response = await client.get(
                "/api/get_order.php",
                params={"phone": phone}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("status"):
                return {"orders": [], "total_orders": 0}
            
            # API may return single order or list - normalize to list
            order_data = data.get("order")
            if order_data:
                # Single order returned
                orders = [order_data] if isinstance(order_data, dict) else order_data
            else:
                orders = data.get("orders", [])
            
            # Apply limit
            orders = orders[:limit]
            
            return {
                "orders": orders,
                "total_orders": len(orders),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"CHICX API error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to get orders: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX API request error: {e}")
            raise ChicxAPIError(f"Failed to connect to CHICX API: {e}")

    # =========================================================================
    # Order Confirmation Callback
    # =========================================================================

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def confirm_order(
        self,
        order_id: str,
        confirmed: bool,
        confirmation_notes: str | None = None,
    ) -> dict[str, Any]:
        """Send order confirmation result back to CHICX backend.
        
        Called after customer confirms/rejects order via phone call.
        
        Args:
            order_id: The order ID that was confirmed
            confirmed: True if customer confirmed, False if rejected
            confirmation_notes: Optional notes (e.g., "Customer not reachable")
            
        Returns:
            API response from CHICX backend
        """
        client = await self._get_client()
        
        payload = {
            "order_id": order_id,
            "confirmed": confirmed,
            "confirmation_method": "voice_call",
        }
        
        if confirmation_notes:
            payload["notes"] = confirmation_notes
        
        logger.info(f"Sending order confirmation to CHICX: {order_id} = {confirmed}")
        
        try:
            response = await client.post(
                "/api/confirm_order.php",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Order confirmation sent successfully: {order_id}")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"CHICX confirm_order error: {e.response.status_code}")
            raise ChicxAPIError(f"Failed to confirm order: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"CHICX confirm_order request error: {e}")
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
