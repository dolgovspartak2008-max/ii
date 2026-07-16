import pytest

from app.application.tenants.use_cases import OwnerDashboard
from app.infrastructure.telegram.business_bot.callbacks import (
    OwnerChatCallback,
    OwnerPanelCallback,
)
from app.infrastructure.telegram.business_bot.router import (
    create_owner_panel_keyboard,
    open_owner_panel,
    parse_business_profile,
)


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


@pytest.mark.asyncio
async def test_open_owner_panel_clears_stale_state_and_renders_dashboard() -> None:
    message = FakeMessage()
    state = FakeState()
    onboarding = FakeOnboarding()

    await open_owner_panel(message, state, 42, onboarding, FakeDashboard())

    assert state.cleared is True
    assert onboarding.owner_ids == [42]
    assert message.answers[0][0] == "Панель управления"
