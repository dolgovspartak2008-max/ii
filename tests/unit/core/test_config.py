import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings(
        telegram_business_bot_token="business-token",
        telegram_access_bot_token="access-token",
        admin_telegram_id=42,
        telegram_access_webhook_secret="0123456789abcdef0123456789abcdef",
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


def test_settings_require_admin_and_webhook_secret() -> None:
    settings = Settings(
        telegram_business_bot_token="business-token",
        telegram_access_bot_token="access-token",
        admin_telegram_id=42,
        telegram_access_webhook_secret="0123456789abcdef0123456789abcdef",
    )

    assert settings.admin_telegram_id == 42
    assert (
        settings.telegram_access_webhook_secret.get_secret_value()
        == "0123456789abcdef0123456789abcdef"
    )
