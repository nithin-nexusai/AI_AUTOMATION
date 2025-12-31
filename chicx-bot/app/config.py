"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_debug: bool = False
    app_port: int = 8000
    app_secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://chicx:chicx_dev_pass@localhost:5432/chicx"
    database_pool_size: int = 5

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp (Meta Cloud API)
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""

    # DeepSeek LLM
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    # OpenRouter (LLM)
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-001"  # LLM model for chat

    # Google Gemini (Embeddings only)
    gemini_api_key: str = ""
    embedding_model: str = "text-embedding-004"  # Embedding model

    # OpenAI (optional, for fallback)
    openai_api_key: str = ""

    # Bolna (Voice Agent) - Managed Platform
    # Bolna handles all voice AI, telephony, and call recording
    bolna_base_url: str = "https://api.bolna.dev"
    bolna_api_key: str = ""  # Required - get from Bolna dashboard
    bolna_webhook_secret: str = ""  # Required for webhook authentication
    bolna_confirmation_agent_id: str = ""  # Agent ID for outbound confirmation calls

    # Admin Dashboard
    admin_api_key: str = ""  # API key for admin endpoints

    # Recording Retention
    recording_retention_days: int = 90  # Days to keep recordings (0 = forever)
    recording_cleanup_enabled: bool = True  # Enable automatic cleanup

    # CHICX Backend
    chicx_api_base_url: str = ""
    chicx_api_key: str = ""

    # Shiprocket (for live shipment tracking)
    shiprocket_email: str = ""  # API user email
    shiprocket_password: str = ""  # API user password
    shiprocket_webhook_secret: str = ""

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
