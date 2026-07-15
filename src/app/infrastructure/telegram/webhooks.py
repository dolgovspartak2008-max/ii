"""Telegram webhook registration for the deployed application."""

from typing import Protocol

from app.core.config import Settings


class TelegramWebhookBot(Protocol):
    """Subset of Telegram Bot API needed to register a webhook."""

    async def set_webhook(self, url: str) -> bool:
        """Tell Telegram where to send updates."""


async def configure_telegram_webhooks(
    settings: Settings,
    access_bot: TelegramWebhookBot,
    business_bot: TelegramWebhookBot,
) -> None:
    """Point each bot at its own secret-protected public endpoint."""
    public_url = str(settings.public_base_url).rstrip("/")
    await access_bot.set_webhook(
        f"{public_url}/webhooks/access/"
        f"{settings.telegram_access_webhook_secret.get_secret_value()}"
    )
    await business_bot.set_webhook(
        f"{public_url}/webhooks/business/"
        f"{settings.telegram_business_webhook_secret.get_secret_value()}"
    )
