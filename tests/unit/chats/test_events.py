from app.infrastructure.telegram.business_bot.events import is_owner_message


def test_owner_message_is_identified_by_telegram_id() -> None:
    assert is_owner_message(owner_telegram_id=42, sender_telegram_id=42) is True
    assert is_owner_message(owner_telegram_id=42, sender_telegram_id=7) is False
