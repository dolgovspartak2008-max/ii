"""Aiogram handlers for applying for service access."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.application.access.use_cases import (
    ApplicationNotFound,
    ApproveAccessApplication,
    ForbiddenReviewer,
    RejectAccessApplication,
    SubmitAccessApplication,
)
from app.domain.access.entities import InvalidApplicationTransition
from app.infrastructure.telegram.access_bot.callbacks import AccessReviewCallback

SUBMIT_CALLBACK = "access:submit"


def create_access_router(
    submit: SubmitAccessApplication,
) -> Router:
    """Create isolated handlers for the separate access application bot."""
    router = Router(name="access-application")

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(
            "Это бот заявок на доступ к сервису. После одобрения вы сможете "
            "настроить основной бот для своего бизнеса.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Подать заявку",
                            callback_data=SUBMIT_CALLBACK,
                        )
                    ]
                ]
            ),
        )

    @router.callback_query(F.data == SUBMIT_CALLBACK)
    async def submit_application(callback: CallbackQuery) -> None:
        user = callback.from_user
        if user is None:
            await callback.answer(
                "Не удалось определить пользователя.", show_alert=True
            )
            return

        result = await submit.execute(user.id, user.username)
        if result.is_new:
            await callback.answer("Заявка отправлена.", show_alert=True)
        else:
            await callback.answer(
                "Ваша заявка уже находится на рассмотрении.", show_alert=True
            )

    return router


def create_access_review_router(
    approve: ApproveAccessApplication,
    reject: RejectAccessApplication,
) -> Router:
    """Handle administrator review controls in the main Telegram bot."""
    router = Router(name="access-review")

    @router.callback_query(AccessReviewCallback.filter())
    async def review_application(
        callback: CallbackQuery,
        callback_data: AccessReviewCallback,
    ) -> None:
        user = callback.from_user
        if user is None:
            await callback.answer(
                "Не удалось определить проверяющего.", show_alert=True
            )
            return

        reviewer = approve if callback_data.action == "approve" else reject
        try:
            result = await reviewer.execute(callback_data.application_id, user.id)
        except ForbiddenReviewer:
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        except ApplicationNotFound:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        except InvalidApplicationTransition:
            await callback.answer("Заявка уже рассмотрена.", show_alert=True)
            return

        if result.is_changed:
            await callback.answer("Решение сохранено.")
        else:
            await callback.answer("Это решение уже сохранено.")

    return router
