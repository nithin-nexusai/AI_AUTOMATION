"""Pytest configuration and shared fixtures for CHICX Bot tests."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.base import Base
from app.main import app


# ============================================================================
# Test Settings
# ============================================================================

@pytest.fixture(scope="session")
def test_settings(monkeypatch_session) -> Settings:
    """Override settings for testing."""
    import os
    
    # Set test environment variables to override .env file
    test_env = {
        "APP_ENV": "testing",
        "APP_DEBUG": "true",
        "DATABASE_URL": os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://test:test@127.0.0.1:5432/chicx_test"
        ),
        "REDIS_URL": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "WHATSAPP_PHONE_NUMBER_ID": "test_phone_id",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "test_business_id",
        "WHATSAPP_ACCESS_TOKEN": "test_token",
        "WHATSAPP_VERIFY_TOKEN": "test_verify",
        "WHATSAPP_APP_SECRET": "test_secret",
        "OPENROUTER_API_KEY": "test_openrouter_key",
        "GEMINI_API_KEY": "test_gemini_key",
        "CHICX_API_KEY": "test_chicx_key",
        "BOLNA_API_KEY": "test_bolna_key",
        "ADMIN_API_KEY": "test_admin_key",
    }
    
    # Apply environment variables
    for key, value in test_env.items():
        monkeypatch_session.setenv(key, value)
    
    # Create settings with test values (will read from env vars we just set)
    return Settings()


@pytest.fixture(scope="session", autouse=True)
def override_settings(test_settings: Settings) -> Generator:
    """Override get_settings for all tests."""
    # Clear the lru_cache so get_settings() returns fresh settings
    get_settings.cache_clear()
    
    # Override for dependency injection
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    # Monkey-patch get_settings to return test settings
    from app import config
    original_get_settings = config.get_settings
    config.get_settings = lambda: test_settings
    
    yield
    
    # Restore
    app.dependency_overrides.clear()
    config.get_settings = original_get_settings
    get_settings.cache_clear()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch fixture."""
    from _pytest.monkeypatch import MonkeyPatch
    m = MonkeyPatch()
    yield m
    m.undo()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine(test_settings):
    """Create test database engine using PostgreSQL."""
    from sqlalchemy.exc import OperationalError
    
    # Create engine with connection pool settings optimized for testing
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        connect_args={
            "timeout": 30,
            "command_timeout": 30,
        }
    )
    
    # Retry connection with exponential backoff
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Test connection and create tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except (OperationalError, OSError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8 seconds
                print(f"Database connection attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)  # Use async sleep
            else:
                print(f"Failed to connect to database after {max_retries} attempts")
                raise
    
    yield engine
    
    # Clean up: drop all tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception as e:
        print(f"Warning: Failed to clean up database: {e}")
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
def test_client(mock_redis) -> TestClient:
    """Create FastAPI test client with mocked Redis."""
    # Initialize app state with mock Redis
    app.state.redis = mock_redis
    client = TestClient(app)
    yield client
    # Clean up
    if hasattr(app.state, 'redis'):
        delattr(app.state, 'redis')


@pytest_asyncio.fixture
async def async_test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Mock External Services
# ============================================================================

@pytest.fixture
def mock_openrouter() -> MagicMock:
    """Mock OpenRouter LLM client."""
    mock = MagicMock()
    mock.chat_with_tools = AsyncMock(return_value={
        "content": "Test response from LLM",
        "iterations": 1,
        "tool_calls_made": [],
    })
    return mock


@pytest.fixture
def mock_whatsapp_api() -> MagicMock:
    """Mock WhatsApp Cloud API."""
    mock = MagicMock()
    mock.post = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"messages": [{"id": "wamid.test123"}]}
    ))
    return mock


@pytest.fixture
def mock_chicx_api() -> MagicMock:
    """Mock CHICX backend API."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"products": [], "orders": []}
    ))
    return mock


@pytest.fixture
def mock_bolna_api() -> MagicMock:
    """Mock Bolna voice API."""
    mock = MagicMock()
    mock.post = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"call_id": "test_call_123"}
    ))
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {
        "phone": "+919876543210",
        "name": "Test User",
    }


@pytest.fixture
def sample_whatsapp_message() -> dict:
    """Sample WhatsApp webhook message payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "test_entry_id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "919876543210",
                                "phone_number_id": "test_phone_id",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": "919876543210",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.test123",
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {"body": "Hello"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_product_data() -> dict:
    """Sample product data for testing."""
    return {
        "id": "prod_123",
        "name": "Red Silk Saree",
        "description": "Beautiful red silk saree",
        "price": 1999.00,
        "category": "sarees",
        "url": "https://chicx.in/products/red-silk-saree",
        "images": ["https://chicx.in/images/saree1.jpg"],
        "in_stock": True,
    }


@pytest.fixture
def sample_order_data() -> dict:
    """Sample order data for testing."""
    return {
        "order_id": "CHX12345",
        "status": "shipped",
        "customer_phone": "+919876543210",
        "items": [
            {
                "product_id": "prod_123",
                "name": "Red Silk Saree",
                "quantity": 1,
                "price": 1999.00,
            }
        ],
        "total": 1999.00,
        "tracking_number": "TRACK123",
        "estimated_delivery": "2024-01-15",
    }


@pytest.fixture
def sample_faq_data() -> dict:
    """Sample FAQ data for testing."""
    return {
        "question": "What is your return policy?",
        "answer": "We offer 7-day returns on all products. Items must be unused and in original packaging.",
        "category": "returns",
    }


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Add any cleanup logic here
    pass
