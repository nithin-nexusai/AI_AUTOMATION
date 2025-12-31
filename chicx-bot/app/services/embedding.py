"""Embedding service for pgvector semantic search.

This module provides:
- Embedding generation using Google Gemini API
- Semantic search for FAQs using pgvector cosine similarity

Note: Products are fetched from CHICX backend API, not stored locally.
"""

import logging
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.models.knowledge import Embedding, FAQ, SourceType

logger = logging.getLogger(__name__)

# Embedding model configuration - Gemini text-embedding-004 outputs 768 dimensions
EMBEDDING_DIMENSION = 768

# Module-level HTTP client for connection reuse
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Get or create the module-level HTTP client for connection reuse."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def shutdown_embedding_client() -> None:
    """Shutdown the HTTP client. Call during app shutdown."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


class EmbeddingService:
    """Service for generating and searching vector embeddings.

    Uses pgvector for efficient similarity search on FAQ embeddings.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the embedding service.

        Args:
            db: Async database session
        """
        self._db = db
        self._settings = get_settings()

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def generate_embedding(self, text_content: str) -> list[float]:
        """Generate embedding vector for text using Google Gemini.

        Args:
            text_content: Text to embed

        Returns:
            Embedding vector as list of floats (768 dimensions)
        """
        api_key = self._settings.gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured for embeddings")

        model = self._settings.embedding_model or "text-embedding-004"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"

        client = _get_http_client()

        try:
            response = await client.post(
                url,
                json={
                    "model": f"models/{model}",
                    "content": {"parts": [{"text": text_content}]},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding API error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def search_faqs(
        self,
        query: str,
        category: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Search FAQs using semantic similarity.

        Args:
            query: User's question
            category: Optional FAQ category filter
            limit: Maximum results

        Returns:
            List of matching FAQs with question, answer, and relevance score
        """
        # Generate embedding for the query
        logger.info(f"Searching FAQs: query='{query}', category={category}")
        try:
            query_embedding = await self.generate_embedding(query)
            logger.debug(f"Generated embedding with {len(query_embedding)} dimensions")
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # Join with FAQs table to get full FAQ data and apply category filter
        # Note: Using cast() syntax instead of :: to avoid parameter name conflicts
        # Using 'FAQ' (uppercase) to match the SourceType enum value
        # Using ILIKE for case-insensitive category matching
        if category:
            sql = text("""
                SELECT
                    f.id,
                    f.question,
                    f.answer,
                    f.category,
                    1 - (e.embedding <=> cast(:embedding as vector)) as relevance_score
                FROM embeddings e
                JOIN faqs f ON e.source_id = f.id
                WHERE e.source_type = 'FAQ'
                    AND f.is_active = true
                    AND LOWER(f.category) = LOWER(:category)
                ORDER BY e.embedding <=> cast(:embedding as vector)
                LIMIT :limit
            """)
            result = await self._db.execute(
                sql,
                {"embedding": embedding_str, "category": category, "limit": limit}
            )
        else:
            sql = text("""
                SELECT
                    f.id,
                    f.question,
                    f.answer,
                    f.category,
                    1 - (e.embedding <=> cast(:embedding as vector)) as relevance_score
                FROM embeddings e
                JOIN faqs f ON e.source_id = f.id
                WHERE e.source_type = 'FAQ'
                    AND f.is_active = true
                ORDER BY e.embedding <=> cast(:embedding as vector)
                LIMIT :limit
            """)
            result = await self._db.execute(
                sql,
                {"embedding": embedding_str, "limit": limit}
            )

        rows = result.fetchall()

        # Filter by minimum relevance threshold
        # Lowered from 0.5 to 0.35 to catch more semantic variations
        min_relevance = 0.35
        faqs = []
        for row in rows:
            if row.relevance_score >= min_relevance:
                faqs.append({
                    "id": str(row.id),
                    "question": row.question,
                    "answer": row.answer,
                    "category": row.category,
                    "relevance_score": round(float(row.relevance_score), 3),
                })

        logger.info(f"FAQ search returned {len(faqs)} results (filtered from {len(rows)} candidates)")
        return faqs

    async def create_embedding_for_faq(self, faq: FAQ) -> Embedding | None:
        """Create embedding for a FAQ entry.

        Args:
            faq: FAQ model instance

        Returns:
            Created Embedding or None if failed
        """
        # Combine question and answer for embedding
        text_to_embed = f"Question: {faq.question}\nAnswer: {faq.answer}"

        try:
            embedding_vector = await self.generate_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Failed to generate embedding for FAQ {faq.id}: {e}")
            return None

        embedding = Embedding(
            source_type=SourceType.FAQ,
            source_id=faq.id,
            chunk_text=text_to_embed,
            embedding=embedding_vector,
        )
        self._db.add(embedding)
        await self._db.flush()

        return embedding

    async def delete_embeddings_for_faq(self, faq_id: str) -> int:
        """Delete all embeddings for a FAQ.

        Args:
            faq_id: UUID of the FAQ

        Returns:
            Number of embeddings deleted
        """
        result = await self._db.execute(
            text("""
                DELETE FROM embeddings
                WHERE source_type = 'faq' AND source_id = :source_id
                RETURNING id
            """),
            {"source_id": faq_id}
        )
        deleted = result.fetchall()
        return len(deleted)
