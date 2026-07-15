"""PostgreSQL persistence for tenant-scoped Telegram Business chats."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.chats.entities import BusinessConnection, ChatState, CustomerChat
from app.infrastructure.persistence.models.chats import (
    BusinessConnectionModel,
    CustomerChatModel,
)


class PostgresBusinessChatRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_connection(
        self, connection_id: str, tenant_id: UUID, owner_id: int, is_enabled: bool
    ) -> None:
        statement = (
            insert(BusinessConnectionModel)
            .values(
                connection_id=connection_id,
                tenant_id=tenant_id,
                owner_telegram_id=owner_id,
                is_enabled=is_enabled,
            )
            .on_conflict_do_update(
                index_elements=[BusinessConnectionModel.connection_id],
                set_={"is_enabled": is_enabled, "owner_telegram_id": owner_id},
            )
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)

    async def get_connection(self, connection_id: str) -> BusinessConnection | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(BusinessConnectionModel).where(
                    BusinessConnectionModel.connection_id == connection_id
                )
            )
        if model is None:
            return None
        return BusinessConnection(
            model.connection_id,
            model.tenant_id,
            model.owner_telegram_id,
            model.is_enabled,
        )

    async def open_customer_chat(
        self, tenant_id: UUID, telegram_chat_id: int
    ) -> CustomerChat:
        statement = (
            insert(CustomerChatModel)
            .values(
                tenant_id=tenant_id,
                telegram_chat_id=telegram_chat_id,
                state=ChatState.ACTIVE.value,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    CustomerChatModel.tenant_id,
                    CustomerChatModel.telegram_chat_id,
                ]
            )
            .returning(CustomerChatModel)
        )
        async with self._session_factory() as session, session.begin():
            model = (await session.execute(statement)).scalar_one_or_none()
            if model is None:
                model = await session.scalar(
                    select(CustomerChatModel).where(
                        CustomerChatModel.tenant_id == tenant_id,
                        CustomerChatModel.telegram_chat_id == telegram_chat_id,
                    )
                )
        return CustomerChat(
            model.tenant_id, model.telegram_chat_id, ChatState(model.state)
        )

    async def mark_human_handoff(
        self, tenant_id: UUID, telegram_chat_id: int
    ) -> CustomerChat:
        statement = (
            update(CustomerChatModel)
            .where(
                CustomerChatModel.tenant_id == tenant_id,
                CustomerChatModel.telegram_chat_id == telegram_chat_id,
            )
            .values(state=ChatState.HUMAN_HANDOFF.value)
            .returning(CustomerChatModel)
        )
        async with self._session_factory() as session, session.begin():
            model = (await session.execute(statement)).scalar_one()
        return CustomerChat(
            model.tenant_id, model.telegram_chat_id, ChatState(model.state)
        )
