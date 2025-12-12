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

    # Embeddings (OpenAI or compatible)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-ada-002"
    embedding_base_url: str = "https://api.openai.com/v1"

    # Exotel (Voice)
    exotel_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""

    # Bolna (Voice Agent)
    bolna_base_url: str = "http://localhost:5001"
    bolna_api_key: str = ""

    # CHICX Backend
    chicx_api_base_url: str = ""
    chicx_api_key: str = ""

    # Shiprocket
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
