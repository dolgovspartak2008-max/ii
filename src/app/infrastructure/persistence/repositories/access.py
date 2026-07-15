"""PostgreSQL repository for access applications."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.access.ports import (
    ApplicationReview,
    ApplicationSubmission,
)
from app.domain.access.entities import AccessApplication, ApplicationStatus
from app.infrastructure.persistence.models.access import AccessApplicationModel


class PostgresAccessApplicationRepository:
    """Persist access applications through an async SQLAlchemy session factory."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_pending(self, telegram_id: int) -> ApplicationSubmission:
        """Create an application or return the already persisted one."""
        statement = (
            insert(AccessApplicationModel)
            .values(telegram_id=telegram_id, status=ApplicationStatus.PENDING.value)
            .on_conflict_do_nothing(index_elements=[AccessApplicationModel.telegram_id])
            .returning(AccessApplicationModel)
        )
        async with self._session_factory() as session, session.begin():
            model = (await session.execute(statement)).scalar_one_or_none()
            is_new = model is not None
            if not is_new:
                model = await session.scalar(
                    select(AccessApplicationModel).where(
                        AccessApplicationModel.telegram_id == telegram_id
                    )
                )

        if model is None:
            raise RuntimeError("Access application was not persisted.")

        return ApplicationSubmission(
            application=self._to_domain(model),
            is_new=is_new,
        )

    async def review(
        self,
        application_id: UUID,
        status: ApplicationStatus,
        reviewer_telegram_id: int,
    ) -> ApplicationReview | None:
        """Review only a pending application, safely handling duplicate callbacks."""
        statement = (
            update(AccessApplicationModel)
            .where(
                AccessApplicationModel.id == application_id,
                AccessApplicationModel.status == ApplicationStatus.PENDING.value,
            )
            .values(
                status=status.value,
                reviewed_at=func.now(),
                reviewer_telegram_id=reviewer_telegram_id,
            )
            .returning(AccessApplicationModel)
        )
        async with self._session_factory() as session, session.begin():
            model = (await session.execute(statement)).scalar_one_or_none()
            is_changed = model is not None
            if not is_changed:
                model = await session.scalar(
                    select(AccessApplicationModel).where(
                        AccessApplicationModel.id == application_id
                    )
                )

        if model is None:
            return None
        return ApplicationReview(
            application=self._to_domain(model),
            is_changed=is_changed,
        )

    async def get_by_telegram_id(self, telegram_id: int) -> AccessApplication | None:
        """Load one access application for the prospective tenant owner."""
        async with self._session_factory() as session:
            model = await session.scalar(
                select(AccessApplicationModel).where(
                    AccessApplicationModel.telegram_id == telegram_id
                )
            )
        return self._to_domain(model) if model is not None else None

    @staticmethod
    def _to_domain(model: AccessApplicationModel) -> AccessApplication:
        return AccessApplication(
            id=model.id,
            telegram_id=model.telegram_id,
            status=ApplicationStatus(model.status),
        )
