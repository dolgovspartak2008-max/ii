import asyncio
import secrets

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.chats.entities import ChatState
from app.infrastructure.persistence.repositories.chats import (
    PostgresBusinessChatRepository,
)
from app.infrastructure.persistence.repositories.tenants import PostgresTenantRepository


def test_connection_resolves_tenant_and_owner_reply_starts_handoff() -> None:
    async def scenario() -> None:
        engine = create_async_engine("postgresql+asyncpg://app:app@localhost:5432/app")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        tenants = PostgresTenantRepository(sessions)
        chats = PostgresBusinessChatRepository(sessions)
        owner_id = secrets.randbelow(10**12) + 10**12
        tenant = await tenants.create_for_owner(owner_id)
        connection_id = f"connection-{secrets.token_hex(8)}"
        customer_chat_id = secrets.randbelow(10**12) + 10**12

        await chats.upsert_connection(connection_id, tenant.tenant.id, owner_id, True)
        connection = await chats.get_connection(connection_id)
        opened = await chats.open_customer_chat(
            connection.tenant_id,
            customer_chat_id,
        )
        handed_off = await chats.mark_human_handoff(
            connection.tenant_id,
            customer_chat_id,
        )

        assert opened.state is ChatState.ACTIVE
        assert handed_off.state is ChatState.HUMAN_HANDOFF
        await engine.dispose()

    asyncio.run(scenario())
