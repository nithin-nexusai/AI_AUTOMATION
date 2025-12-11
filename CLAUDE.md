# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CHICX AI Platform - a conversational commerce solution for CHICX (D2C women's fashion e-commerce):
- **WhatsApp Bot**: Product discovery, order tracking, FAQ support via Meta Cloud API
- **Voice Agent**: Inbound IVR using Bolna framework with Exotel telephony
- **LLM**: DeepSeek Chat API for natural language processing
- **Read-only bot**: Users browse and track orders; all purchases happen on the CHICX website

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL 16 + pgvector (vector search for RAG)
- **Cache**: Redis 7
- **Container**: Docker Compose
- **Voice**: Bolna (self-hosted) + Whisper STT + Google TTS
- **External APIs**: Meta WhatsApp, DeepSeek, Exotel, Shiprocket

## Development Commands

```bash
# Start all services (dev mode with hot reload)
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Run without Docker
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Seed data
python scripts/seed_products.py
python scripts/seed_faqs.py
python scripts/generate_embeddings.py

# Local webhook testing
ngrok http 8000
```

## Project Structure

```
chicx-bot/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings from env vars
│   ├── api/
│   │   ├── webhooks/        # WhatsApp, Exotel, Shiprocket, CHICX
│   │   └── admin/           # Health, sync endpoints
│   ├── core/
│   │   ├── llm.py           # DeepSeek client
│   │   ├── tools.py         # 5 LLM tool definitions
│   │   └── prompts.py       # System prompts
│   ├── services/            # Business logic (whatsapp, products, orders, faq)
│   ├── models/              # SQLAlchemy models
│   └── schemas/             # Pydantic schemas
├── bolna/                   # Voice agent config
├── scripts/                 # Seeding and embedding scripts
└── tests/
```

## Architecture

### Data Flow
- **WhatsApp**: User → Meta API → `/webhooks/whatsapp` → DeepSeek → Response
- **Voice**: User → Exotel → Bolna → Whisper (STT) → DeepSeek → Google TTS

### Database Tables (12 total)
- **Core**: users, conversations, messages, orders, order_events
- **Knowledge**: products, faqs, embeddings (pgvector)
- **Voice**: calls, call_transcripts
- **System**: templates, analytics_events

### LLM Tools (5)
1. `search_products` - Search catalog by query/category/price
2. `get_product_details` - Get specific product info
3. `get_order_status` - Track order by ID
4. `get_order_history` - List user's past orders
5. `search_faq` - Semantic search for FAQs (RAG)

## Key Design Decisions

- **Read-only bot**: No cart/checkout - users directed to website for purchases
- **Bilingual**: English + Tamil with Tanglish code-switching support
- **pgvector**: Embedded in PostgreSQL for FAQ/product semantic search
- **Self-hosted**: No managed services; Docker Compose on EC2 t3.medium
- **Webhook-driven**: Order updates via Shiprocket and CHICX backend webhooks

## Environment Variables

Required in `.env` (see `.env.example`):
- `DATABASE_URL`, `REDIS_URL` - Data layer connections
- `WHATSAPP_*` - Meta API credentials (phone ID, token, verify token, app secret)
- `DEEPSEEK_API_KEY` - LLM API key
- `EXOTEL_*` - Voice telephony credentials
- `CHICX_API_*` - Backend integration

## Documentation

Specification documents are in `/docs/`:
- `CHICX_Technical_Architecture_updated.docx` - Full system architecture
- `CHICX_API_Specification.docx` - Webhook and API endpoints
- `CHICX_Database_Schema.docx` - Complete table definitions
- `CHICX_Environment_Setup.docx` - Local dev setup guide
- `CHICX_LLM_Prompt_Library.docx` - System prompts and templates
- `CHICX_Conversation_Flows.docx` - Bot flow diagrams
