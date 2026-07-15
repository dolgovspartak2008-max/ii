import pytest

from app.domain.tenants.entities import (
    BusinessProfile,
    InvalidBusinessProfile,
    Tenant,
)


def test_tenant_belongs_to_exactly_one_owner() -> None:
    tenant = Tenant.create(owner_telegram_id=42)

    assert tenant.owner_telegram_id == 42


def test_profile_rejects_blank_business_name() -> None:
    with pytest.raises(InvalidBusinessProfile):
        BusinessProfile.create(name="   ", description="Описание")


def test_profile_trims_owner_supplied_text() -> None:
    profile = BusinessProfile.create(
        name="  Кофейня  ", description="  Кофе и десерты "
    )

    assert profile.name == "Кофейня"
    assert profile.description == "Кофе и десерты"
