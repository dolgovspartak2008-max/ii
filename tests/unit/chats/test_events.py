from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.domain.chats.entities import BusinessConnection
from app.infrastructure.persistence.repositories.chats import (
    PostgresBusinessChatRepository,
)
from app.infrastructure.telegram.business_bot.events import (
    deliver_business_reply,
    is_owner_message,
)


def test_owner_message_is_identified_by_telegram_id() -> None:
    assert is_owner_message(owner_telegram_id=42, sender_telegram_id=42) is True
    assert is_owner_message(owner_telegram_id=42, sender_telegram_id=7) is False


def test_message_sent_by_business_bot_is_not_an_owner_handoff() -> None:
    assert (
        is_owner_message(
            owner_telegram_id=42,
            sender_telegram_id=42,
            sender_business_bot=object(),
        )
        is False
    )


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


class CapturingSession:
    def __init__(self) -> None:
        self.statement = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    def begin(self):
        return self

    async def execute(self, statement) -> None:
        self.statement = statement


class EmptyResult:
    def scalar_one_or_none(self):
        return None


class ResumeCapturingSession(CapturingSession):
    async def execute(self, statement):
        self.statement = statement
        return EmptyResult()


class CapturingSessionFactory:
    def __init__(self, session: CapturingSession) -> None:
        self.session = session

    def __call__(self) -> CapturingSession:
        return self.session


@pytest.mark.asyncio
async def test_new_connection_replaces_the_tenants_previous_connection() -> None:
    session = CapturingSession()
    repository = PostgresBusinessChatRepository(CapturingSessionFactory(session))

    await repository.upsert_connection("new-connection", uuid4(), 42, True)

    assert session.statement is not None
    sql = " ".join(
        str(session.statement.compile(dialect=postgresql.dialect())).split()
    )
    assert "ON CONFLICT (tenant_id) DO UPDATE" in sql
    assert "connection_id = excluded.connection_id" in sql


@pytest.mark.asyncio
async def test_resume_ai_scopes_update_to_tenant_chat_and_handoff_state() -> None:
    session = ResumeCapturingSession()
    repository = PostgresBusinessChatRepository(CapturingSessionFactory(session))

    resumed = await repository.resume_ai(uuid4(), 700)

    assert resumed is False
    assert session.statement is not None
    sql = " ".join(
        str(session.statement.compile(dialect=postgresql.dialect())).split()
    )
    assert "UPDATE customer_chats SET state=" in sql
    assert "customer_chats.tenant_id" in sql
    assert "customer_chats.telegram_chat_id" in sql
    assert "customer_chats.state" in sql


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
