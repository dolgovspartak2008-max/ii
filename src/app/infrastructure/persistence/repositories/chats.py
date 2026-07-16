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
        statement = insert(BusinessConnectionModel).values(
            connection_id=connection_id,
            tenant_id=tenant_id,
            owner_telegram_id=owner_id,
            is_enabled=is_enabled,
        )
        statement = (
            statement
            .on_conflict_do_update(
                index_elements=[BusinessConnectionModel.tenant_id],
                set_={
                    "connection_id": statement.excluded.connection_id,
                    "is_enabled": statement.excluded.is_enabled,
                    "owner_telegram_id": statement.excluded.owner_telegram_id,
                },
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

    async def get_customer_chat(
        self, tenant_id: UUID, telegram_chat_id: int
    ) -> CustomerChat | None:
        """Read exactly one tenant-scoped customer chat."""
        async with self._session_factory() as session:
            model = await session.scalar(
                select(CustomerChatModel).where(
                    CustomerChatModel.tenant_id == tenant_id,
                    CustomerChatModel.telegram_chat_id == telegram_chat_id,
                )
            )
        if model is None:
            return None
        return CustomerChat(
            model.tenant_id, model.telegram_chat_id, ChatState(model.state)
        )

    async def list_handoff_chats(
        self, tenant_id: UUID, limit: int = 10
    ) -> list[CustomerChat]:
        """List a bounded set of chats the tenant owner is handling manually."""
        statement = (
            select(CustomerChatModel)
            .where(
                CustomerChatModel.tenant_id == tenant_id,
                CustomerChatModel.state == ChatState.HUMAN_HANDOFF.value,
            )
            .order_by(CustomerChatModel.created_at.asc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            models = (await session.scalars(statement)).all()
        return [
            CustomerChat(
                model.tenant_id,
                model.telegram_chat_id,
                ChatState(model.state),
            )
            for model in models
        ]

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

    async def resume_ai(self, tenant_id: UUID, telegram_chat_id: int) -> bool:
        """Switch one tenant-scoped handed-off chat back to active."""
        statement = (
            update(CustomerChatModel)
            .where(
                CustomerChatModel.tenant_id == tenant_id,
                CustomerChatModel.telegram_chat_id == telegram_chat_id,
                CustomerChatModel.state == ChatState.HUMAN_HANDOFF.value,
            )
            .values(state=ChatState.ACTIVE.value)
            .returning(CustomerChatModel.id)
        )
        async with self._session_factory() as session, session.begin():
            result = await session.execute(statement)
        return result.scalar_one_or_none() is not None
