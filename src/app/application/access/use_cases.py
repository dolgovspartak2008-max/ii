"""Workflows for applying for and reviewing service access."""

from uuid import UUID

from app.application.access.ports import (
    AccessApplicationRepository,
    AccessNotificationPort,
    AccessOutboxPort,
    ApplicationReview,
    ApplicationSubmission,
)
from app.domain.access.entities import ApplicationStatus, InvalidApplicationTransition


class ForbiddenReviewer(PermissionError):
    """Raised when a non-administrator attempts to review an application."""


class ApplicationNotFound(LookupError):
    """Raised when an application cannot be found for review."""


class SubmitAccessApplication:
    """Accept a request and alert the administrator once."""

    def __init__(
        self,
        repository: AccessApplicationRepository,
        notifier: AccessNotificationPort,
        outbox: AccessOutboxPort | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._outbox = outbox

    async def execute(
        self,
        telegram_id: int,
        username: str | None,
    ) -> ApplicationSubmission:
        """Submit an application and notify the administrator if it is new."""
        result = await self._repository.create_pending(telegram_id)
        if result.is_new:
            try:
                await self._notifier.notify_admin(result.application, username)
            except Exception:
                if self._outbox is None:
                    raise
                await self._outbox.enqueue(
                    "access_application_submitted",
                    {
                        "application_id": str(result.application.id),
                        "username": username or "",
                    },
                )
        return result


class ApproveAccessApplication:
    """Approve an application on behalf of the configured administrator."""

    def __init__(
        self,
        repository: AccessApplicationRepository,
        notifier: AccessNotificationPort,
        admin_telegram_id: int,
        outbox: AccessOutboxPort | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._admin_telegram_id = admin_telegram_id
        self._outbox = outbox

    async def execute(
        self,
        application_id: UUID,
        reviewer_id: int,
    ) -> ApplicationReview:
        """Approve a pending application and alert its applicant."""
        if reviewer_id != self._admin_telegram_id:
            raise ForbiddenReviewer("Only the configured administrator may approve.")

        result = await self._repository.review(
            application_id,
            ApplicationStatus.APPROVED,
            reviewer_id,
        )
        if result is None:
            raise ApplicationNotFound("Access application was not found.")
        if not result.is_changed:
            if result.application.status is not ApplicationStatus.APPROVED:
                raise InvalidApplicationTransition("Application was already reviewed.")
            return result

        try:
            await self._notifier.notify_applicant(result.application)
        except Exception:
            if self._outbox is None:
                raise
            await self._outbox.enqueue(
                "access_application_reviewed",
                {
                    "application_id": str(result.application.id),
                    "status": result.application.status.value,
                },
            )
        return result


class RejectAccessApplication:
    """Reject an application on behalf of the configured administrator."""

    def __init__(
        self,
        repository: AccessApplicationRepository,
        notifier: AccessNotificationPort,
        admin_telegram_id: int,
        outbox: AccessOutboxPort | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._admin_telegram_id = admin_telegram_id
        self._outbox = outbox

    async def execute(
        self,
        application_id: UUID,
        reviewer_id: int,
    ) -> ApplicationReview:
        """Reject a pending application and alert its applicant."""
        if reviewer_id != self._admin_telegram_id:
            raise ForbiddenReviewer("Only the configured administrator may reject.")

        result = await self._repository.review(
            application_id,
            ApplicationStatus.REJECTED,
            reviewer_id,
        )
        if result is None:
            raise ApplicationNotFound("Access application was not found.")
        if not result.is_changed:
            if result.application.status is not ApplicationStatus.REJECTED:
                raise InvalidApplicationTransition("Application was already reviewed.")
            return result

        try:
            await self._notifier.notify_applicant(result.application)
        except Exception:
            if self._outbox is None:
                raise
            await self._outbox.enqueue(
                "access_application_reviewed",
                {
                    "application_id": str(result.application.id),
                    "status": result.application.status.value,
                },
            )
        return result
