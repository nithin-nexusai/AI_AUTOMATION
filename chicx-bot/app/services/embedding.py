"""Embedding service for pgvector semantic search.

This module provides:
- Embedding generation using OpenAI-compatible API
- Semantic search for FAQs using pgvector cosine similarity

Note: Products are fetched from CHICX backend API, not stored locally.
"""

import logging
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.knowledge import Embedding, FAQ, SourceType

logger = logging.getLogger(__name__)

# Embedding model configuration
EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-ada-002 dimension


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
        self._client: AsyncOpenAI | None = None

    async def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client for embeddings."""
        if self._client is None:
            api_key = self._settings.openai_api_key or self._settings.deepseek_api_key
            base_url = self._settings.embedding_base_url or "https://api.openai.com/v1"

            if not api_key:
                raise ValueError("No API key configured for embeddings (OPENAI_API_KEY or DEEPSEEK_API_KEY)")

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        return self._client

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        client = await self._get_client()
        model = self._settings.embedding_model or "text-embedding-ada-002"

        try:
            response = await client.embeddings.create(
                model=model,
                input=text,
            )
            return response.data[0].embedding
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
        try:
            query_embedding = await self.generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # Join with FAQs table to get full FAQ data and apply category filter
        if category:
            sql = text("""
                SELECT
                    f.id,
                    f.question,
                    f.answer,
                    f.category,
                    1 - (e.embedding <=> :embedding::vector) as relevance_score
                FROM embeddings e
                JOIN faqs f ON e.source_id = f.id
                WHERE e.source_type = 'faq'
                    AND f.is_active = true
                    AND f.category = :category
                ORDER BY e.embedding <=> :embedding::vector
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
                    1 - (e.embedding <=> :embedding::vector) as relevance_score
                FROM embeddings e
                JOIN faqs f ON e.source_id = f.id
                WHERE e.source_type = 'faq'
                    AND f.is_active = true
                ORDER BY e.embedding <=> :embedding::vector
                LIMIT :limit
            """)
            result = await self._db.execute(
                sql,
                {"embedding": embedding_str, "limit": limit}
            )

        rows = result.fetchall()

        # Filter by minimum relevance threshold
        min_relevance = 0.5
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
