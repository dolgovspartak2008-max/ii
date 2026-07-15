import asyncio
from uuid import UUID

import pytest

from app.application.tenants.ports import TenantCreation
from app.application.tenants.use_cases import (
    OnboardApprovedOwner,
    OwnerNotApproved,
    UpdateBusinessProfile,
)
from app.domain.access.entities import AccessApplication, ApplicationStatus
from app.domain.tenants.entities import BusinessProfile, Tenant


class FakeAccessApprovals:
    def __init__(self, application: AccessApplication | None) -> None:
        self.application = application

    async def get_by_telegram_id(self, telegram_id: int) -> AccessApplication | None:
        return self.application


class FakeTenants:
    def __init__(self) -> None:
        self.tenants: dict[int, Tenant] = {}
        self.profiles: dict[UUID, BusinessProfile] = {}

    async def create_for_owner(self, owner_telegram_id: int) -> TenantCreation:
        tenant = self.tenants.get(owner_telegram_id)
        if tenant is not None:
            return TenantCreation(tenant=tenant, is_new=False)
        tenant = Tenant.create(owner_telegram_id)
        self.tenants[owner_telegram_id] = tenant
        return TenantCreation(tenant=tenant, is_new=True)

    async def get_by_owner(self, owner_telegram_id: int) -> Tenant | None:
        return self.tenants.get(owner_telegram_id)

    async def update_business_profile(
        self,
        tenant_id: UUID,
        name: str,
        description: str,
    ) -> BusinessProfile:
        profile = BusinessProfile.create(name, description)
        self.profiles[tenant_id] = profile
        return profile


def test_onboarding_rejects_an_unapproved_owner() -> None:
    async def scenario() -> None:
        onboarding = OnboardApprovedOwner(FakeAccessApprovals(None), FakeTenants())

        with pytest.raises(OwnerNotApproved):
            await onboarding.execute(owner_telegram_id=42)

    asyncio.run(scenario())


def test_approved_owner_can_update_only_own_business_profile() -> None:
    async def scenario() -> None:
        approved = AccessApplication.submit(telegram_id=42)
        approved.status = ApplicationStatus.APPROVED
        tenants = FakeTenants()
        onboarding = OnboardApprovedOwner(FakeAccessApprovals(approved), tenants)
        await onboarding.execute(owner_telegram_id=42)
        update = UpdateBusinessProfile(tenants)

        profile = await update.execute(
            owner_telegram_id=42,
            name="Кофейня",
            description="Кофе и десерты",
        )

        assert profile.name == "Кофейня"
        assert len(tenants.profiles) == 1

    asyncio.run(scenario())
