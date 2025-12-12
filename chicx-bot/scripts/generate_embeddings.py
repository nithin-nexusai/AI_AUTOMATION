#!/usr/bin/env python3
"""Generate embeddings for FAQs using pgvector.

This script:
1. Fetches all active FAQs from the database
2. Generates embeddings using OpenAI's text-embedding-ada-002 model
3. Stores embeddings in the embeddings table for semantic search

Note: Products are fetched from CHICX backend API, not stored locally.

Usage:
    python scripts/generate_embeddings.py
    python scripts/generate_embeddings.py --force  # Regenerate all

Environment variables required:
    - DATABASE_URL: PostgreSQL connection string
    - OPENAI_API_KEY: OpenAI API key for embeddings
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.knowledge import FAQ, Embedding, SourceType
from app.services.embedding import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def generate_faq_embeddings(db: AsyncSession, force: bool = False) -> int:
    """Generate embeddings for all active FAQs.

    Args:
        db: Database session
        force: If True, regenerate all embeddings (delete existing first)

    Returns:
        Number of embeddings generated
    """
    logger.info("Generating FAQ embeddings...")

    if force:
        # Delete existing FAQ embeddings
        await db.execute(
            delete(Embedding).where(Embedding.source_type == SourceType.FAQ)
        )
        await db.commit()
        logger.info("Deleted existing FAQ embeddings")

    # Get all active FAQs
    result = await db.execute(
        select(FAQ).where(FAQ.is_active == True)
    )
    faqs = result.scalars().all()

    if not faqs:
        logger.warning("No active FAQs found")
        return 0

    logger.info(f"Found {len(faqs)} active FAQs")

    embedding_service = EmbeddingService(db)
    count = 0

    for faq in faqs:
        # Check if embedding already exists
        existing = await db.execute(
            select(Embedding).where(
                Embedding.source_type == SourceType.FAQ,
                Embedding.source_id == faq.id
            )
        )
        if existing.scalar_one_or_none() and not force:
            logger.debug(f"Skipping FAQ {faq.id} - embedding exists")
            continue

        try:
            embedding = await embedding_service.create_embedding_for_faq(faq)
            if embedding:
                count += 1
                logger.info(f"Created embedding for FAQ: {faq.question[:50]}...")
            else:
                logger.warning(f"Failed to create embedding for FAQ {faq.id}")
        except Exception as e:
            logger.error(f"Error creating embedding for FAQ {faq.id}: {e}")

    await db.commit()
    logger.info(f"Generated {count} FAQ embeddings")
    return count


async def main(force: bool) -> None:
    """Main entry point for embedding generation."""
    logger.info("Starting FAQ embedding generation...")

    async with async_session_maker() as db:
        total = await generate_faq_embeddings(db, force)
        logger.info(f"Total embeddings generated: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate embeddings for FAQs"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all embeddings (deletes existing)"
    )

    args = parser.parse_args()

    asyncio.run(main(args.force))
