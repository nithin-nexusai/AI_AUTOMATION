# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CHICX AI Platform - a conversational commerce solution for CHICX (D2C women's fashion e-commerce):
- **WhatsApp Bot**: Product discovery, order tracking, FAQ support via Meta Cloud API
- **Voice Agent**: Inbound/outbound calls using Bolna (managed platform) + Whisper STT + Google TTS
- **LLM**: DeepSeek Chat API (OpenAI-compatible)
- **Read-only bot**: Users browse and track orders; all purchases happen on the CHICX website

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async), Alembic
- **Database**: PostgreSQL 16 + pgvector (vector search for RAG)
- **Cache**: Redis 7
- **Container**: Docker Compose
- **External APIs**: Meta WhatsApp, DeepSeek, Bolna, Shiprocket, CHICX Backend

## Development Commands

```bash
# Start all services (dev mode with hot reload)
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f app

# Run without Docker
cd chicx-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Linting and type checking
ruff check app/
mypy app/

# Run tests
pytest
pytest tests/test_file.py::test_function  # Single test
pytest --cov=app  # With coverage

# Generate FAQ embeddings
python scripts/generate_embeddings.py
python scripts/import_faqs.py

# Local webhook testing
ngrok http 8000
```

## Architecture

### Data Flow
- **WhatsApp**: User → Meta API → `/webhooks/whatsapp` → DeepSeek + Tools → Response
- **Voice**: Caller → Bolna → `/webhooks/bolna/tool` → Execute tool → Bolna TTS
- **Outbound Confirmation**: CHICX Backend → `/webhooks/chicx/confirm-order` → Bolna call → Confirm result

### Data Sources
- **Real-time from CHICX API**: Products, Orders (no local storage)
- **Local with pgvector**: FAQs stored locally for instant semantic search
- **Redis**: Conversation context (last 20 messages, 24h TTL), message deduplication

### LLM Tools (6)
1. `search_products` - Search catalog by query/category/price
2. `get_product_details` - Get specific product info by ID
3. `get_order_status` - Track order by ID
4. `get_order_history` - List user's past orders (phone-based)
5. `search_faq` - Semantic search for FAQs using pgvector
6. `track_shipment` - Live tracking by AWB via Shiprocket

### Webhook Endpoints
- `POST /webhooks/whatsapp` - Meta Cloud API messages (signature verified)
- `GET /webhooks/whatsapp` - Meta webhook verification
- `POST /webhooks/bolna/call-complete` - Call completion data
- `POST /webhooks/bolna/transcript` - Call transcripts
- `POST /webhooks/bolna/tool` - LLM tool execution during calls
- `POST /webhooks/chicx/confirm-order` - Trigger outbound confirmation call
- `POST /webhooks/chicx/cart-reminder` - Send cart abandonment reminder
- `POST /webhooks/chicx/order-update` - Order status change notification

## Key Design Decisions

- **Read-only bot**: No cart/checkout - users directed to website for purchases
- **Multilingual**: English, Tamil, Malayalam, Hindi with code-switching (Tanglish, Manglish, Hinglish)
- **Phone-based identity**: Users identified by WhatsApp/call phone number (no login)
- **Async-first**: FastAPI + asyncpg + aioredis for concurrent handling
- **Webhook-driven**: All external events trigger webhooks, no polling
- **Signature verification**: HMAC SHA256 for WhatsApp, custom headers for Bolna/CHICX

## Environment Variables

Required in `.env` (see `chicx-bot/.env.example`):
- `DATABASE_URL`, `REDIS_URL` - Data layer connections
- `WHATSAPP_*` - Meta API credentials (phone ID, token, verify token, app secret)
- `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` - LLM API
- `OPENAI_API_KEY`, `EMBEDDING_MODEL` - Embeddings for FAQ search
- `BOLNA_API_KEY`, `BOLNA_WEBHOOK_SECRET` - Voice platform
- `CHICX_API_BASE_URL`, `CHICX_API_KEY` - Backend integration
- `SHIPROCKET_WEBHOOK_SECRET` - Shipment tracking
- `ADMIN_API_KEY` - Admin API authentication

## External API Integration

Products and orders come from the CHICX backend team - this bot is read-only and fetches data via:
- `GET /api/get_products.php` - Product search
- `GET /api/get_order.php?phone=X` - Orders by phone
- `GET /api/order_status.php?order_id=X` - Order status

See `docs/API_REFERENCE.md` for complete API documentation.
