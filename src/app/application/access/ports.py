"""Ports used by the access application workflows."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.access.entities import AccessApplication, ApplicationStatus


@dataclass(frozen=True)
class ApplicationSubmission:
    """Result of accepting a new or duplicate application submission."""

    application: AccessApplication
    is_new: bool


@dataclass(frozen=True)
class ApplicationReview:
    """Result of changing an application's review status."""

    application: AccessApplication
    is_changed: bool


class AccessApplicationRepository(Protocol):
    """Persistent storage for access applications."""

    async def create_pending(self, telegram_id: int) -> ApplicationSubmission:
        """Create a pending application or return its existing record."""

    async def review(
        self,
        application_id: UUID,
        status: ApplicationStatus,
        reviewer_telegram_id: int,
    ) -> ApplicationReview | None:
        """Review a pending application atomically."""


class AccessNotificationPort(Protocol):
    """Telegram notification operations for an access application."""

    async def notify_admin(
        self,
        application: AccessApplication,
        username: str | None,
    ) -> None:
        """Notify the administrator about a newly created application."""

    async def notify_applicant(self, application: AccessApplication) -> None:
        """Notify an applicant about the review result."""


class AccessOutboxPort(Protocol):
    """Durable queue for notifications that could not be delivered immediately."""

    async def enqueue(self, event_type: str, payload: dict[str, str]) -> None:
        """Persist a notification event for later delivery."""
