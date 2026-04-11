#!/bin/bash

# CHICX Bot Initialization Script
# This script sets up the database, runs migrations, and generates embeddings

set -e  # Exit on error

echo "🚀 Starting CHICX Bot initialization..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure it first:"
    echo "  cp .env.example .env"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found .env file"

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check required environment variables
REQUIRED_VARS=(
    "DATABASE_URL"
    "REDIS_URL"
    "OPENROUTER_API_KEY"
    "WHATSAPP_VERIFY_TOKEN"
    "WHATSAPP_ACCESS_TOKEN"
)

echo ""
echo "📋 Checking required environment variables..."
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
        echo -e "${RED}✗${NC} $var is not set"
    else
        echo -e "${GREEN}✓${NC} $var is set"
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required environment variables. Please configure them in .env${NC}"
    exit 1
fi

# Check if PostgreSQL is accessible
echo ""
echo "🔌 Testing database connection..."
if python3 -c "
import asyncio
import asyncpg
import sys
from urllib.parse import urlparse

async def test_connection():
    try:
        parsed = urlparse('$DATABASE_URL')
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else None,
            timeout=5
        )
        await conn.close()
        return True
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Database connection successful"
else
    echo -e "${RED}❌ Cannot connect to database${NC}"
    echo "Please check your DATABASE_URL in .env"
    exit 1
fi

# Check if Redis is accessible
echo ""
echo "🔌 Testing Redis connection..."
if python3 -c "
import redis
import sys
from urllib.parse import urlparse

try:
    parsed = urlparse('$REDIS_URL')
    r = redis.Redis(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        password=parsed.password,
        socket_connect_timeout=5
    )
    r.ping()
    print('Redis connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Redis connection failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Redis connection successful"
else
    echo -e "${YELLOW}⚠${NC}  Cannot connect to Redis (optional for development)"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi

# Run database migrations
echo ""
echo "🗄️  Running database migrations..."
if alembic upgrade head; then
    echo -e "${GREEN}✓${NC} Database migrations completed"
else
    echo -e "${RED}❌ Database migration failed${NC}"
    exit 1
fi

# Check if FAQs exist
echo ""
echo "📚 Checking FAQ data..."
FAQ_COUNT=$(python3 -c "
import asyncio
import asyncpg
from urllib.parse import urlparse

async def count_faqs():
    try:
        parsed = urlparse('$DATABASE_URL')
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else None
        )
        count = await conn.fetchval('SELECT COUNT(*) FROM faqs WHERE is_active = true')
        await conn.close()
        return count or 0
    except:
        return 0

print(asyncio.run(count_faqs()))
" 2>/dev/null || echo "0")

if [ "$FAQ_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC}  No FAQs found in database"
    echo ""
    echo "Would you like to import FAQs now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if [ -f "scripts/import_faqs.py" ]; then
            echo "Running FAQ import..."
            python3 scripts/import_faqs.py
            echo -e "${GREEN}✓${NC} FAQs imported"
        else
            echo -e "${YELLOW}⚠${NC}  FAQ import script not found"
        fi
    fi
else
    echo -e "${GREEN}✓${NC} Found $FAQ_COUNT active FAQs"
fi

# Generate embeddings
echo ""
echo "🧠 Checking FAQ embeddings..."
EMBEDDING_COUNT=$(python3 -c "
import asyncio
import asyncpg
from urllib.parse import urlparse

async def count_embeddings():
    try:
        parsed = urlparse('$DATABASE_URL')
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else None
        )
        count = await conn.fetchval(\"SELECT COUNT(*) FROM embeddings WHERE source_type = 'FAQ'\")
        await conn.close()
        return count or 0
    except:
        return 0

print(asyncio.run(count_embeddings()))
" 2>/dev/null || echo "0")

if [ "$EMBEDDING_COUNT" -eq 0 ] && [ "$FAQ_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  No embeddings found for FAQs"
    echo "Generating embeddings (this may take a few minutes)..."
    if [ -f "scripts/generate_embeddings.py" ]; then
        python3 scripts/generate_embeddings.py
        echo -e "${GREEN}✓${NC} Embeddings generated"
    else
        echo -e "${RED}❌ Embedding generation script not found${NC}"
    fi
elif [ "$EMBEDDING_COUNT" -lt "$FAQ_COUNT" ]; then
    echo -e "${YELLOW}⚠${NC}  Only $EMBEDDING_COUNT/$FAQ_COUNT FAQs have embeddings"
    echo "Regenerating embeddings..."
    python3 scripts/generate_embeddings.py --force
    echo -e "${GREEN}✓${NC} Embeddings regenerated"
else
    echo -e "${GREEN}✓${NC} All FAQs have embeddings ($EMBEDDING_COUNT)"
fi

# Final checks
echo ""
echo "🔍 Running final validation..."

# Test OpenRouter API key
echo -n "Testing OpenRouter API key... "
if python3 -c "
import requests
import sys

try:
    response = requests.get(
        'https://openrouter.ai/api/v1/models',
        headers={'Authorization': f'Bearer $OPENROUTER_API_KEY'},
        timeout=10
    )
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${YELLOW}⚠${NC}  OpenRouter API key may be invalid"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Initialization complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "  • Database: Connected and migrated"
echo "  • Redis: Connected"
echo "  • FAQs: $FAQ_COUNT active"
echo "  • Embeddings: $EMBEDDING_COUNT generated"
echo ""
echo "🚀 You can now start the application:"
echo "  Development: uvicorn app.main:app --reload"
echo "  Production:  uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "📝 Don't forget to:"
echo "  1. Configure your WhatsApp webhook URL in Meta Developer Console"
echo "  2. Set up ngrok or similar for local development"
echo "  3. Test the /health endpoint"
echo ""

# Made with Bob
