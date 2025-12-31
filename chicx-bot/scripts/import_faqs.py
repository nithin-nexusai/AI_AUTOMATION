#!/usr/bin/env python3
"""FAQ Import Script

Processes FAQ documents (PDF/DOCX) and imports them into the database with embeddings.

Usage:
    python scripts/import_faqs.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db.session import async_session_maker
from app.models.knowledge import FAQ
from app.services.embedding import EmbeddingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        import pypdf
        
        text = ""
        with open(file_path, "rb") as f:
            pdf = pypdf.PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except ImportError:
        logger.error("pypdf not installed. Install with: pip install pypdf")
        return ""
    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {e}")
        return ""


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    try:
        import docx
        
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except ImportError:
        logger.error("python-docx not installed. Install with: pip install python-docx")
        return ""
    except Exception as e:
        logger.error(f"Error reading DOCX {file_path}: {e}")
        return ""


def parse_faqs_from_text(text: str, source_file: str) -> list[dict[str, str]]:
    """Parse FAQs from text.
    
    Looks for Q&A patterns like:
    - Q: ... A: ...
    - Question: ... Answer: ...
    - Numbered lists with questions
    """
    faqs = []
    lines = text.split("\n")
    
    current_question = None
    current_answer = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for question patterns
        if (line.startswith("Q:") or line.startswith("Question:") or 
            line.lower().startswith("q.") or "?" in line):
            # Save previous Q&A if exists
            if current_question and current_answer:
                faqs.append({
                    "question": current_question,
                    "answer": " ".join(current_answer).strip(),
                    "category": extract_category(current_question),
                })
            
            # Start new question
            current_question = line.replace("Q:", "").replace("Question:", "").replace("q.", "").strip()
            current_answer = []
        
        # Check for answer patterns
        elif (line.startswith("A:") or line.startswith("Answer:") or 
              line.lower().startswith("a.")) and current_question:
            answer_text = line.replace("A:", "").replace("Answer:", "").replace("a.", "").strip()
            current_answer.append(answer_text)
        
        # Continuation of answer
        elif current_question and not line.startswith(("Q:", "Question:", "q.")):
            current_answer.append(line)
    
    # Save last Q&A
    if current_question and current_answer:
        faqs.append({
            "question": current_question,
            "answer": " ".join(current_answer).strip(),
            "category": extract_category(current_question),
        })
    
    # If no Q&A patterns found, chunk the text
    if not faqs:
        logger.warning(f"No Q&A patterns found in {source_file}, chunking text instead")
        faqs = chunk_text_as_faqs(text)
    
    return faqs


def extract_category(question: str) -> str:
    """Extract category from question text."""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ["ship", "deliver", "tracking"]):
        return "Shipping"
    elif any(word in question_lower for word in ["return", "refund", "exchange"]):
        return "Returns"
    elif any(word in question_lower for word in ["payment", "pay", "cod", "cash"]):
        return "Payment"
    elif any(word in question_lower for word in ["order", "cancel", "modify"]):
        return "Orders"
    elif any(word in question_lower for word in ["product", "size", "quality"]):
        return "Products"
    elif any(word in question_lower for word in ["contact", "support", "help"]):
        return "Support"
    else:
        return "General"


def chunk_text_as_faqs(text: str, chunk_size: int = 500) -> list[dict[str, str]]:
    """Chunk text into FAQ-like entries when no Q&A pattern is found."""
    chunks = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para_length = len(para)
        
        if current_length + para_length > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "question": chunk_text[:100] + "...",  # First 100 chars as question
                "answer": chunk_text,
                "category": "General",
            })
            current_chunk = []
            current_length = 0
        
        current_chunk.append(para)
        current_length += para_length
    
    # Save last chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "question": chunk_text[:100] + "...",
            "answer": chunk_text,
            "category": "General",
        })
    
    return chunks


async def import_faqs(docs_dir: Path):
    """Import FAQs from documents directory."""
    settings = get_settings()

    # Find all PDF and DOCX files
    pdf_files = list(docs_dir.glob("*.pdf"))
    docx_files = list(docs_dir.glob("*.docx"))
    all_files = pdf_files + docx_files
    
    if not all_files:
        logger.warning(f"No PDF or DOCX files found in {docs_dir}")
        return
    
    logger.info(f"Found {len(all_files)} files to process")
    
    all_faqs = []
    
    # Extract text from each file
    for file_path in all_files:
        logger.info(f"Processing {file_path.name}...")
        
        if file_path.suffix == ".pdf":
            text = extract_text_from_pdf(file_path)
        elif file_path.suffix == ".docx":
            text = extract_text_from_docx(file_path)
        else:
            continue
        
        if not text:
            logger.warning(f"No text extracted from {file_path.name}")
            continue
        
        # Parse FAQs from text
        faqs = parse_faqs_from_text(text, file_path.name)
        logger.info(f"Extracted {len(faqs)} FAQs from {file_path.name}")
        all_faqs.extend(faqs)
    
    if not all_faqs:
        logger.error("No FAQs extracted from any files")
        return
    
    logger.info(f"Total FAQs to import: {len(all_faqs)}")
    
    # Import into database
    async with async_session_maker() as db:
        embedding_service = EmbeddingService(db)
        
        for i, faq_data in enumerate(all_faqs, 1):
            try:
                # Check if FAQ already exists
                existing = await db.execute(
                    select(FAQ).where(FAQ.question == faq_data["question"])
                )
                if existing.scalar_one_or_none():
                    logger.info(f"[{i}/{len(all_faqs)}] FAQ already exists, skipping: {faq_data['question'][:50]}...")
                    continue
                
                # Create FAQ
                faq = FAQ(
                    question=faq_data["question"],
                    answer=faq_data["answer"],
                    category=faq_data["category"],
                    is_active=True,
                )
                db.add(faq)
                await db.flush()  # Get the ID
                
                # Generate and store embedding in separate Embedding table
                logger.info(f"[{i}/{len(all_faqs)}] Generating embedding for: {faq_data['question'][:50]}...")
                embedding = await embedding_service.create_embedding_for_faq(faq)
                
                if not embedding:
                    logger.warning(f"Failed to create embedding for FAQ {faq.id}")
                
                await db.commit()
                
                logger.info(f"[{i}/{len(all_faqs)}] ✓ Imported: {faq_data['question'][:50]}...")
            
            except Exception as e:
                logger.error(f"Error importing FAQ: {e}")
                await db.rollback()
                continue
    
    logger.info(f"✅ FAQ import complete! Imported {len(all_faqs)} FAQs")


async def main():
    """Main entry point."""
    docs_dir = Path(__file__).parent.parent / "docs" / "faqs"
    
    if not docs_dir.exists():
        logger.error(f"Directory not found: {docs_dir}")
        logger.info("Please create the directory and add your FAQ documents (PDF/DOCX)")
        return
    
    logger.info(f"Importing FAQs from: {docs_dir}")
    await import_faqs(docs_dir)


if __name__ == "__main__":
    # Add missing import at top
    from sqlalchemy import select
    
    asyncio.run(main())
