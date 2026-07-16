"""Aiogram implementation of access application notifications."""

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.access.entities import AccessApplication, ApplicationStatus
from app.infrastructure.telegram.access_bot.callbacks import AccessReviewCallback


class AiogramAccessNotifier:
    """Send review controls to the main bot and results to the intake bot."""

    def __init__(
        self,
        applicant_bot: Bot,
        review_bot: Bot,
        admin_telegram_id: int,
    ) -> None:
        self._applicant_bot = applicant_bot
        self._review_bot = review_bot
        self._admin_telegram_id = admin_telegram_id

    async def notify_admin(
        self,
        application: AccessApplication,
        username: str | None,
    ) -> None:
        """Send one reviewable notification to the global administrator."""
        user_label = f"@{username}" if username else "без username"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Одобрить",
                        callback_data=AccessReviewCallback(
                            action="approve",
                            application_id=application.id,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="Отклонить",
                        callback_data=AccessReviewCallback(
                            action="reject",
                            application_id=application.id,
                        ).pack(),
                    ),
                ]
            ]
        )
        await self._review_bot.send_message(
            self._admin_telegram_id,
            "Новая заявка на доступ\n"
            f"Пользователь: {user_label}\n"
            f"Telegram ID: {application.telegram_id}",
            reply_markup=keyboard,
        )

    async def notify_applicant(self, application: AccessApplication) -> None:
        """Tell the applicant that the administrator reviewed the request."""
        text = {
            ApplicationStatus.APPROVED: (
                "Заявка одобрена. Откройте основного бота и завершите "
                "настройку бизнеса."
            ),
            ApplicationStatus.REJECTED: (
                "Заявка отклонена. Если это ошибка, свяжитесь с администратором."
            ),
        }.get(application.status)
        if text is None:
            raise ValueError(
                "Only an approved or rejected application can be announced."
            )
        await self._applicant_bot.send_message(application.telegram_id, text)
