"""Validated application configuration loaded from the environment."""

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Immutable runtime settings for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    public_base_url: AnyHttpUrl
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/app"
    redis_url: str = "redis://redis:6379/0"
    telegram_business_bot_token: SecretStr = Field(min_length=1)
    telegram_access_bot_token: SecretStr = Field(min_length=1)
    admin_telegram_id: int = Field(gt=0)
    telegram_access_webhook_secret: SecretStr = Field(min_length=32)
    telegram_business_webhook_secret: SecretStr = Field(min_length=32)
    openrouter_api_key: SecretStr = Field(min_length=1)
    openrouter_model: str = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide settings instance."""
    return Settings()
