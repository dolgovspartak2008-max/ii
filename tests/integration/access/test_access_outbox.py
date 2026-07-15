import asyncio
import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.persistence.models.access import AccessOutboxEventModel
from app.infrastructure.persistence.repositories.outbox import (
    PostgresAccessOutboxRepository,
)


def test_outbox_event_is_durably_persisted() -> None:
    async def scenario() -> None:
        engine = create_async_engine("postgresql+asyncpg://app:app@localhost:5432/app")
        outbox = PostgresAccessOutboxRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        event_type = f"test.{secrets.token_hex(8)}"

        await outbox.enqueue(event_type, {"application_id": "example"})

        async with engine.connect() as connection:
            count = await connection.scalar(
                select(func.count())
                .select_from(AccessOutboxEventModel)
                .where(AccessOutboxEventModel.event_type == event_type)
            )
        assert count == 1
        await engine.dispose()

    asyncio.run(scenario())
