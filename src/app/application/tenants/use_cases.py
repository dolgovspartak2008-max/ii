"""Approved-owner onboarding and tenant-scoped business settings workflows."""

from app.application.tenants.ports import (
    AccessApprovalPort,
    TenantCreation,
    TenantPort,
)
from app.domain.access.entities import ApplicationStatus
from app.domain.tenants.entities import BusinessProfile


class OwnerNotApproved(PermissionError):
    """Raised when an owner has no approved access application."""


class TenantNotFound(LookupError):
    """Raised when an owner attempts setup before successful onboarding."""


class OnboardApprovedOwner:
    """Create the one tenant allowed for an approved Telegram owner."""

    def __init__(self, approvals: AccessApprovalPort, tenants: TenantPort) -> None:
        self._approvals = approvals
        self._tenants = tenants

    async def execute(self, owner_telegram_id: int) -> TenantCreation:
        """Verify approval before creating or returning the owner's tenant."""
        application = await self._approvals.get_by_telegram_id(owner_telegram_id)
        if application is None or application.status is not ApplicationStatus.APPROVED:
            raise OwnerNotApproved("Owner must have an approved access application.")
        return await self._tenants.create_for_owner(owner_telegram_id)


class UpdateBusinessProfile:
    """Change business context only after resolving the authenticated owner."""

    def __init__(self, tenants: TenantPort) -> None:
        self._tenants = tenants

    async def execute(
        self,
        owner_telegram_id: int,
        name: str,
        description: str,
    ) -> BusinessProfile:
        """Resolve a tenant by owner before updating that tenant's profile."""
        tenant = await self._tenants.get_by_owner(owner_telegram_id)
        if tenant is None:
            raise TenantNotFound("Owner has not completed onboarding.")
        return await self._tenants.update_business_profile(
            tenant.id,
            name,
            description,
        )
