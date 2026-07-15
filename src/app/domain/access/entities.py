"""Business rules for service access applications."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4


class ApplicationStatus(StrEnum):
    """Lifecycle states for an application to use the service."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class InvalidApplicationTransition(ValueError):
    """Raised when an application lifecycle transition is not allowed."""


@dataclass
class AccessApplication:
    """A request from a Telegram user to access the service."""

    id: UUID
    telegram_id: int
    status: ApplicationStatus = ApplicationStatus.PENDING

    @classmethod
    def submit(cls, telegram_id: int) -> "AccessApplication":
        """Create a new pending application."""
        return cls(id=uuid4(), telegram_id=telegram_id)

    def approve(self) -> None:
        """Approve a pending application."""
        self._change_status(ApplicationStatus.APPROVED)

    def reject(self) -> None:
        """Reject a pending application."""
        self._change_status(ApplicationStatus.REJECTED)

    def _change_status(self, next_status: ApplicationStatus) -> None:
        if self.status is not ApplicationStatus.PENDING:
            raise InvalidApplicationTransition(
                f"Cannot change application from {self.status} to {next_status}."
            )
        self.status = next_status
