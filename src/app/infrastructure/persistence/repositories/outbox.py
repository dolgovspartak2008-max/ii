"""PostgreSQL outbox repository for access notifications."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.persistence.models.access import AccessOutboxEventModel


class PostgresAccessOutboxRepository:
    """Persist notification retries independently of Telegram availability."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def enqueue(self, event_type: str, payload: dict[str, str]) -> None:
        """Store an event that can be retried by an outbox worker."""
        event = AccessOutboxEventModel(event_type=event_type, payload=payload)
        async with self._session_factory() as session, session.begin():
            session.add(event)
