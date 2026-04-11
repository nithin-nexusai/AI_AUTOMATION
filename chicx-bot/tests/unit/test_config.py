"""Unit tests for configuration module."""

import pytest
from app.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """Test Settings class."""

    def test_settings_defaults(self):
        """Test default settings values.
        
        Note: In test environment, app_env is set to 'testing' via environment variables.
        """
        settings = Settings(
            database_url="postgresql://test",
            openrouter_api_key="test_key",
            app_debug=False,  # Explicitly set to avoid .env override
        )
        
        # In test environment, app_env is 'testing' (set by conftest.py)
        assert settings.app_env == "testing"
        assert settings.app_debug is False
        assert settings.app_port == 8000
        assert settings.database_pool_size == 5

    def test_settings_is_development(self):
        """Test is_development property."""
        settings = Settings(
            app_env="development",
            database_url="postgresql://test",
            openrouter_api_key="test_key",
        )
        assert settings.is_development is True
        assert settings.is_production is False

    def test_settings_is_production(self):
        """Test is_production property."""
        settings = Settings(
            app_env="production",
            database_url="postgresql://test",
            openrouter_api_key="test_key",
        )
        assert settings.is_production is True
        assert settings.is_development is False

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_settings_from_env(self, monkeypatch):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("APP_PORT", "9000")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")
        
        settings = Settings()
        assert settings.app_env == "testing"
        assert settings.app_port == 9000


