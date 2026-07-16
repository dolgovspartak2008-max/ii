"""Ports and result types for tenant workflows."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.access.entities import AccessApplication
from app.domain.tenants.entities import BusinessProfile, Tenant


@dataclass(frozen=True)
class TenantCreation:
    """Result of creating or finding the owner's tenant."""

    tenant: Tenant
    is_new: bool


class AccessApprovalPort(Protocol):
    """Read access-application status for a prospective tenant owner."""

    async def get_by_telegram_id(self, telegram_id: int) -> AccessApplication | None:
        """Return the owner's access application, if one exists."""


class TenantPort(Protocol):
    """Persist and retrieve tenant-scoped business settings."""

    async def create_for_owner(self, owner_telegram_id: int) -> TenantCreation:
        """Create a tenant for an owner or return the existing tenant."""

    async def get_by_owner(self, owner_telegram_id: int) -> Tenant | None:
        """Find a tenant from the authenticated owner identifier."""

    async def update_business_profile(
        self,
        tenant_id: UUID,
        name: str,
        description: str,
    ) -> BusinessProfile:
        """Save business context for one resolved tenant."""

    async def set_ai_enabled(self, tenant_id: UUID, enabled: bool) -> bool:
        """Enable or disable AI replies for one tenant."""

    async def is_ai_enabled(self, tenant_id: UUID) -> bool:
        """Return whether the tenant allows AI replies."""

    async def get_business_profile(self, tenant_id: UUID) -> BusinessProfile | None:
        """Return the business context for one tenant."""
