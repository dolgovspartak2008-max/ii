from app.infrastructure.telegram.business_bot.callbacks import OwnerPanelCallback
from app.infrastructure.telegram.business_bot.router import (
    create_owner_panel_keyboard,
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
