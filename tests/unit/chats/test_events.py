from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.chats.entities import BusinessConnection
from app.infrastructure.telegram.business_bot.events import (
    deliver_business_reply,
    is_owner_message,
)


def test_owner_message_is_identified_by_telegram_id() -> None:
    assert is_owner_message(owner_telegram_id=42, sender_telegram_id=42) is True
    assert is_owner_message(owner_telegram_id=42, sender_telegram_id=7) is False


class FakeReplies:
    def __init__(self, reply: str | None) -> None:
        self.reply = reply
        self.calls: list[tuple] = []

    async def execute(self, tenant_id, chat_id, text):
        self.calls.append((tenant_id, chat_id, text))
        return self.reply


class FakeBot:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def send_message(self, chat_id, text, business_connection_id):
        self.calls.append((chat_id, text, business_connection_id))


@pytest.mark.asyncio
async def test_customer_text_reply_is_delivered_through_business_connection() -> None:
    tenant_id = uuid4()
    connection = BusinessConnection("connection", tenant_id, 42, True)
    message = SimpleNamespace(
        chat=SimpleNamespace(id=700),
        text="Какая цена?",
        business_connection_id="connection",
    )
    replies = FakeReplies("ИИ: Стоимость уточнит владелец.")
    bot = FakeBot()

    await deliver_business_reply(message, connection, replies, bot)

    assert replies.calls == [(tenant_id, 700, "Какая цена?")]
    assert bot.calls == [(700, "ИИ: Стоимость уточнит владелец.", "connection")]


@pytest.mark.asyncio
async def test_non_text_customer_message_is_not_sent_to_ai() -> None:
    connection = BusinessConnection("connection", uuid4(), 42, True)
    message = SimpleNamespace(
        chat=SimpleNamespace(id=700), text=None, business_connection_id="connection"
    )
    replies = FakeReplies("ИИ: Не должно отправиться")
    bot = FakeBot()

    await deliver_business_reply(message, connection, replies, bot)

    assert replies.calls == []
    assert bot.calls == []
