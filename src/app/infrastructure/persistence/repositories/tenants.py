"""PostgreSQL repository for isolated tenants and business profiles."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.tenants.ports import TenantCreation
from app.domain.tenants.entities import BusinessProfile, Tenant
from app.infrastructure.persistence.models.tenants import (
    BusinessProfileModel,
    TenantModel,
)


class PostgresTenantRepository:
    """Read and write tenant records without cross-tenant lookups."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_for_owner(self, owner_telegram_id: int) -> TenantCreation:
        """Create one tenant for an owner or return the existing tenant."""
        statement = (
            insert(TenantModel)
            .values(owner_telegram_id=owner_telegram_id)
            .on_conflict_do_nothing(index_elements=[TenantModel.owner_telegram_id])
            .returning(TenantModel)
        )
        async with self._session_factory() as session, session.begin():
            model = (await session.execute(statement)).scalar_one_or_none()
            is_new = model is not None
            if not is_new:
                model = await session.scalar(
                    select(TenantModel).where(
                        TenantModel.owner_telegram_id == owner_telegram_id
                    )
                )
        if model is None:
            raise RuntimeError("Tenant was not persisted.")
        return TenantCreation(tenant=self._to_tenant(model), is_new=is_new)

    async def get_by_owner(self, owner_telegram_id: int) -> Tenant | None:
        """Find a tenant solely by its authenticated owner identifier."""
        async with self._session_factory() as session:
            model = await session.scalar(
                select(TenantModel).where(
                    TenantModel.owner_telegram_id == owner_telegram_id
                )
            )
        return self._to_tenant(model) if model is not None else None

    async def update_business_profile(
        self,
        tenant_id: UUID,
        name: str,
        description: str,
    ) -> BusinessProfile:
        """Upsert a single profile for the tenant identified by its server-side id."""
        profile = BusinessProfile.create(name, description)
        statement = (
            insert(BusinessProfileModel)
            .values(
                tenant_id=tenant_id,
                name=profile.name,
                description=profile.description,
            )
            .on_conflict_do_update(
                index_elements=[BusinessProfileModel.tenant_id],
                set_={"name": profile.name, "description": profile.description},
            )
            .returning(BusinessProfileModel)
        )
        async with self._session_factory() as session, session.begin():
            model = (await session.execute(statement)).scalar_one()
        return BusinessProfile.create(model.name, model.description)

    async def get_business_profile(self, tenant_id: UUID) -> BusinessProfile | None:
        """Read the profile only for the supplied tenant id."""
        async with self._session_factory() as session:
            model = await session.scalar(
                select(BusinessProfileModel).where(
                    BusinessProfileModel.tenant_id == tenant_id
                )
            )
        if model is None:
            return None
        return BusinessProfile.create(model.name, model.description)

    @staticmethod
    def _to_tenant(model: TenantModel) -> Tenant:
        return Tenant(id=model.id, owner_telegram_id=model.owner_telegram_id)
