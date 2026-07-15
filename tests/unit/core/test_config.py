import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings(
        telegram_business_bot_token="business-token",
        telegram_access_bot_token="access-token",
    )

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_settings_reject_empty_bot_token() -> None:
    with pytest.raises(ValidationError):
        Settings(
            telegram_business_bot_token="",
            telegram_access_bot_token="access-token",
        )
