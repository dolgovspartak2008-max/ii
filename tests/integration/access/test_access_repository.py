import asyncio
import secrets

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.access.entities import ApplicationStatus
from app.infrastructure.persistence.repositories.access import (
    PostgresAccessApplicationRepository,
)


def test_duplicate_submission_returns_existing_pending_application() -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            "postgresql+asyncpg://app:app@localhost:5432/app",
        )
        repository = PostgresAccessApplicationRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        telegram_id = secrets.randbelow(10**12) + 10**12
        first = await repository.create_pending(telegram_id=telegram_id)
        second = await repository.create_pending(telegram_id=telegram_id)

        assert first.application.id == second.application.id
        assert first.is_new is True
        assert second.is_new is False
        assert second.application.status is ApplicationStatus.PENDING
        await engine.dispose()

    asyncio.run(scenario())


def test_review_is_atomic_and_idempotent() -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            "postgresql+asyncpg://app:app@localhost:5432/app",
        )
        repository = PostgresAccessApplicationRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        telegram_id = secrets.randbelow(10**12) + 10**12
        submitted = await repository.create_pending(telegram_id=telegram_id)

        approved = await repository.review(
            submitted.application.id,
            ApplicationStatus.APPROVED,
            reviewer_telegram_id=99,
        )
        repeated = await repository.review(
            submitted.application.id,
            ApplicationStatus.APPROVED,
            reviewer_telegram_id=99,
        )
        conflicting = await repository.review(
            submitted.application.id,
            ApplicationStatus.REJECTED,
            reviewer_telegram_id=99,
        )

        assert approved is not None
        assert approved.is_changed is True
        assert approved.application.status is ApplicationStatus.APPROVED
        assert repeated is not None
        assert repeated.is_changed is False
        assert conflicting is not None
        assert conflicting.application.status is ApplicationStatus.APPROVED
        await engine.dispose()

    asyncio.run(scenario())


def test_application_can_be_loaded_by_owner_telegram_id() -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            "postgresql+asyncpg://app:app@localhost:5432/app",
        )
        repository = PostgresAccessApplicationRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        telegram_id = secrets.randbelow(10**12) + 10**12
        submitted = await repository.create_pending(telegram_id=telegram_id)

        loaded = await repository.get_by_telegram_id(telegram_id)

        assert loaded is not None
        assert loaded.id == submitted.application.id
        await engine.dispose()

    asyncio.run(scenario())
