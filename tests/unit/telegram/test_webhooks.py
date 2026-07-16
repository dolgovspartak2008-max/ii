import pytest

from app.core.config import Settings
from app.infrastructure.telegram.webhooks import configure_telegram_webhooks


class FakeBot:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.commands = []

    async def set_webhook(self, url: str) -> bool:
        self.urls.append(url)
        return True

    async def set_my_commands(self, commands) -> bool:
        self.commands = commands
        return True


@pytest.mark.asyncio
async def test_webhooks_use_public_url_and_separate_secrets() -> None:
    settings = Settings(
        public_base_url="https://example.amvera.tech/",
        telegram_business_bot_token="business-token",
        telegram_access_bot_token="access-token",
        admin_telegram_id=42,
        telegram_access_webhook_secret="0123456789abcdef0123456789abcdef",
        telegram_business_webhook_secret="abcdef0123456789abcdef0123456789",
        openrouter_api_key="openrouter-key",
        openrouter_model="openrouter/auto",
    )
    access_bot = FakeBot()
    business_bot = FakeBot()

    await configure_telegram_webhooks(settings, access_bot, business_bot)

    assert access_bot.urls == [
        "https://example.amvera.tech/webhooks/access/0123456789abcdef0123456789abcdef"
    ]
    assert business_bot.urls == [
        "https://example.amvera.tech/webhooks/business/abcdef0123456789abcdef0123456789"
    ]


@pytest.mark.asyncio
async def test_main_bot_registers_owner_panel_commands() -> None:
    settings = Settings(
        public_base_url="https://example.amvera.tech/",
        telegram_business_bot_token="business-token",
        telegram_access_bot_token="access-token",
        admin_telegram_id=42,
        telegram_access_webhook_secret="0123456789abcdef0123456789abcdef",
        telegram_business_webhook_secret="abcdef0123456789abcdef0123456789",
        openrouter_api_key="openrouter-key",
        openrouter_model="openrouter/auto",
    )
    access_bot = FakeBot()
    business_bot = FakeBot()

    await configure_telegram_webhooks(settings, access_bot, business_bot)

    assert access_bot.commands == []
    assert [(command.command, command.description) for command in business_bot.commands] == [
        ("start", "Открыть панель управления"),
        ("admin", "Открыть панель управления"),
    ]
