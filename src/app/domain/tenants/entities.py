"""Core tenant and business-profile rules."""

from dataclasses import dataclass
from uuid import UUID, uuid4


class InvalidBusinessProfile(ValueError):
    """Raised when a business profile does not have meaningful text."""


@dataclass(frozen=True)
class Tenant:
    """One business workspace owned by one Telegram user."""

    id: UUID
    owner_telegram_id: int

    @classmethod
    def create(cls, owner_telegram_id: int) -> "Tenant":
        """Create a tenant for a positive Telegram owner identifier."""
        if owner_telegram_id <= 0:
            raise ValueError("Owner Telegram ID must be positive.")
        return cls(id=uuid4(), owner_telegram_id=owner_telegram_id)


@dataclass
class BusinessProfile:
    """Business context used to customize the tenant's AI behaviour."""

    name: str
    description: str

    @classmethod
    def create(cls, name: str, description: str) -> "BusinessProfile":
        """Validate and normalize business context."""
        profile = cls(name="", description="")
        profile.update(name, description)
        return profile

    def update(self, name: str, description: str) -> None:
        """Replace the profile with normalized, non-empty values."""
        normalized_name = name.strip()
        normalized_description = description.strip()
        if not normalized_name or not normalized_description:
            raise InvalidBusinessProfile(
                "Business name and description must not be blank."
            )
        self.name = normalized_name
        self.description = normalized_description
