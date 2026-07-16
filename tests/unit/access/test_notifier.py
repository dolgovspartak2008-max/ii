import pytest

from app.domain.access.entities import AccessApplication, ApplicationStatus
from app.infrastructure.telegram.access_bot.notifier import AiogramAccessNotifier


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str, object | None]] = []

    async def send_message(
        self,
        telegram_id: int,
        text: str,
        reply_markup=None,
    ) -> None:
        self.messages.append((telegram_id, text, reply_markup))


@pytest.mark.asyncio
async def test_access_notifier_sends_review_to_main_bot_and_result_to_access_bot(
) -> None:
    access_bot = FakeBot()
    main_bot = FakeBot()
    notifier = AiogramAccessNotifier(
        applicant_bot=access_bot,
        review_bot=main_bot,
        admin_telegram_id=99,
    )
    application = AccessApplication.submit(telegram_id=42)

    await notifier.notify_admin(application, "client")
    application.status = ApplicationStatus.APPROVED
    await notifier.notify_applicant(application)

    assert main_bot.messages[0][0] == 99
    assert main_bot.messages[0][2] is not None
    assert access_bot.messages == [
        (
            42,
            "Заявка одобрена. Откройте основного бота и завершите настройку бизнеса.",
            None,
        )
    ]
