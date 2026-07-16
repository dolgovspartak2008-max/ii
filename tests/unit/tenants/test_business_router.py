from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Message

from app.application.tenants.use_cases import OnboardApprovedOwner, OwnerDashboard
from app.infrastructure.telegram.access_bot.callbacks import AccessReviewCallback
from app.infrastructure.telegram.access_bot.router import create_access_review_router
from app.infrastructure.telegram.business_bot.callbacks import (
    OwnerChatCallback,
    OwnerPanelCallback,
)
from app.infrastructure.telegram.business_bot.router import (
    create_business_router,
    create_owner_panel_keyboard,
    open_owner_panel,
    parse_business_profile,
)
from tests.unit.tenants.test_use_cases import FakeAccessApprovals, FakeTenants


def test_business_command_parser_splits_name_and_description() -> None:
    profile = parse_business_profile("Кофейня | Кофе и десерты")

    assert profile == ("Кофейня", "Кофе и десерты")


def test_business_command_parser_rejects_missing_separator() -> None:
    assert parse_business_profile("Кофейня") is None


def test_owner_panel_callback_round_trip() -> None:
    callback = OwnerPanelCallback.unpack(OwnerPanelCallback(action="toggle_ai").pack())

    assert callback.action == "toggle_ai"


def test_owner_panel_shows_current_ai_state() -> None:
    keyboard = create_owner_panel_keyboard(ai_enabled=True)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert "🤖 ИИ: включён" in labels


def test_owner_panel_has_handoff_chat_button() -> None:
    keyboard = create_owner_panel_keyboard(ai_enabled=True)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert "💬 Диалоги у вас" in labels


def test_owner_chat_callback_round_trip() -> None:
    callback = OwnerChatCallback.unpack(
        OwnerChatCallback(action="resume", telegram_chat_id=700).pack()
    )

    assert callback.telegram_chat_id == 700


class FakeMessage:
    def __init__(self) -> None:
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, reply_markup=None) -> None:
        self.answers.append((text, reply_markup))


class FakeState:
    def __init__(self) -> None:
        self.cleared = False

    async def clear(self) -> None:
        self.cleared = True


class FakeOnboarding:
    def __init__(self) -> None:
        self.owner_ids: list[int] = []

    async def execute(self, owner_id: int) -> None:
        self.owner_ids.append(owner_id)


class FakeDashboard:
    async def execute(self, owner_id: int) -> OwnerDashboard:
        return OwnerDashboard(profile=None, ai_enabled=True)


class FakeProfileUpdater:
    async def execute(self, owner_id: int, name: str, description: str):
        raise AssertionError("Profile update is not part of this scenario.")


class FakeAISettings:
    async def execute(self, owner_id: int, enabled: bool) -> bool:
        return enabled


class FakeHandoffs:
    async def execute(self, owner_id: int):
        return []


class FakeResume:
    async def execute(self, owner_id: int, telegram_chat_id: int) -> bool:
        return False


class FakeReviewer:
    def __init__(self) -> None:
        self.calls: list[tuple[object, int]] = []

    async def execute(self, application_id, reviewer_id: int):
        self.calls.append((application_id, reviewer_id))
        return type("Review", (), {"is_changed": True})()


def create_router_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(
        create_business_router(
            OnboardApprovedOwner(
                FakeAccessApprovals(None),
                FakeTenants(),
                direct_owner_telegram_id=42,
            ),
            FakeProfileUpdater(),
            FakeAISettings(),
            FakeDashboard(),
            FakeHandoffs(),
            FakeResume(),
        )
    )
    return dispatcher


def command_update(command: str) -> dict[str, object]:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": 42, "type": "private"},
            "from": {"id": 42, "is_bot": False, "first_name": "Owner"},
            "text": command,
            "entities": [{"offset": 0, "length": len(command), "type": "bot_command"}],
        },
    }


def panel_callback_update() -> dict[str, object]:
    return {
        "update_id": 2,
        "callback_query": {
            "id": "callback-1",
            "from": {"id": 42, "is_bot": False, "first_name": "Owner"},
            "chat_instance": "chat-instance",
            "data": OwnerPanelCallback(action="show").pack(),
            "message": {
                "message_id": 2,
                "date": 0,
                "chat": {"id": 42, "type": "private"},
                "from": {"id": 1, "is_bot": True, "first_name": "Bot"},
                "text": "Панель управления",
            },
        },
    }


def access_review_callback_update(application_id) -> dict[str, object]:
    return {
        "update_id": 3,
        "callback_query": {
            "id": "review-callback-1",
            "from": {"id": 42, "is_bot": False, "first_name": "Owner"},
            "chat_instance": "chat-instance",
            "data": AccessReviewCallback(
                action="approve", application_id=application_id
            ).pack(),
            "message": {
                "message_id": 3,
                "date": 0,
                "chat": {"id": 42, "type": "private"},
                "from": {"id": 1, "is_bot": True, "first_name": "Bot"},
                "text": "Новая заявка на доступ",
            },
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/start", "/admin"])
async def test_configured_owner_commands_open_panel_through_dispatcher(
    command: str, monkeypatch
) -> None:
    answers: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        answers.append(text)

    monkeypatch.setattr(Message, "answer", answer)
    bot = Bot("123456789:abcdefghijklmnopqrstuvwxyzABCDE")
    try:
        await create_router_dispatcher().feed_raw_update(bot, command_update(command))
    finally:
        await bot.session.close()

    assert answers == ["Панель управления"]


@pytest.mark.asyncio
async def test_panel_button_executes_and_acknowledges_callback_through_dispatcher(
    monkeypatch,
) -> None:
    answers: list[str] = []
    acknowledged: list[str] = []

    async def answer_message(self, text: str, **kwargs) -> None:
        answers.append(text)

    async def answer_callback(self, *args, **kwargs) -> None:
        acknowledged.append(self.id)

    monkeypatch.setattr(Message, "answer", answer_message)
    monkeypatch.setattr(CallbackQuery, "answer", answer_callback)
    bot = Bot("123456789:abcdefghijklmnopqrstuvwxyzABCDE")
    try:
        await create_router_dispatcher().feed_raw_update(bot, panel_callback_update())
    finally:
        await bot.session.close()

    assert answers == ["📋 Профиль бизнеса пока не заполнен."]
    assert acknowledged == ["callback-1"]


@pytest.mark.asyncio
async def test_main_bot_review_callback_approves_application_through_dispatcher(
    monkeypatch,
) -> None:
    reviewer = FakeReviewer()
    acknowledged: list[str] = []
    application_id = uuid4()

    async def answer_callback(self, *args, **kwargs) -> None:
        acknowledged.append(self.id)

    monkeypatch.setattr(CallbackQuery, "answer", answer_callback)
    dispatcher = Dispatcher()
    dispatcher.include_router(create_access_review_router(reviewer, FakeReviewer()))
    bot = Bot("123456789:abcdefghijklmnopqrstuvwxyzABCDE")
    try:
        await dispatcher.feed_raw_update(
            bot,
            access_review_callback_update(application_id),
        )
    finally:
        await bot.session.close()

    assert reviewer.calls == [(application_id, 42)]
    assert acknowledged == ["review-callback-1"]


@pytest.mark.asyncio
async def test_open_owner_panel_clears_stale_state_and_renders_dashboard() -> None:
    message = FakeMessage()
    state = FakeState()
    onboarding = FakeOnboarding()

    await open_owner_panel(message, state, 42, onboarding, FakeDashboard())

    assert state.cleared is True
    assert onboarding.owner_ids == [42]
    assert message.answers[0][0] == "Панель управления"
