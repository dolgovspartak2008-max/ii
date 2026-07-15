import asyncio
import secrets

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.persistence.repositories.tenants import (
    PostgresTenantRepository,
)


def test_owner_has_one_tenant_and_profiles_stay_isolated() -> None:
    async def scenario() -> None:
        engine = create_async_engine("postgresql+asyncpg://app:app@localhost:5432/app")
        repository = PostgresTenantRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        first_owner = secrets.randbelow(10**12) + 10**12
        second_owner = secrets.randbelow(10**12) + 10**12

        first = await repository.create_for_owner(first_owner)
        duplicate = await repository.create_for_owner(first_owner)
        second = await repository.create_for_owner(second_owner)
        profile = await repository.update_business_profile(
            first.tenant.id,
            name="Кофейня",
            description="Кофе и десерты",
        )

        assert first.is_new is True
        assert duplicate.is_new is False
        assert duplicate.tenant.id == first.tenant.id
        assert profile.name == "Кофейня"
        assert await repository.get_business_profile(second.tenant.id) is None
        await engine.dispose()

    asyncio.run(scenario())
