"""Ports and result types for tenant workflows."""

from dataclasses import dataclass

from app.domain.tenants.entities import Tenant


@dataclass(frozen=True)
class TenantCreation:
    """Result of creating or finding the owner's tenant."""

    tenant: Tenant
    is_new: bool
