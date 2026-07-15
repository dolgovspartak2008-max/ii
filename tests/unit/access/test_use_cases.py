from dataclasses import dataclass
from uuid import UUID

import pytest

from app.application.access.ports import ApplicationReview
from app.application.access.use_cases import (
    ApproveAccessApplication,
    ForbiddenReviewer,
    RejectAccessApplication,
    SubmitAccessApplication,
)
from app.domain.access.entities import AccessApplication, ApplicationStatus


@dataclass
class FakeSubmission:
    application: AccessApplication
    is_new: bool


class FakeRepository:
    def __init__(self, application: AccessApplication, is_new: bool = True) -> None:
        self.application = application
        self.is_new = is_new

    async def create_pending(self, telegram_id: int) -> FakeSubmission:
        return FakeSubmission(self.application, is_new=self.is_new)

    async def review(
        self,
        application_id: UUID,
        status: ApplicationStatus,
        reviewer_telegram_id: int,
    ) -> ApplicationReview:
        self.application.status = status
        return ApplicationReview(self.application, is_changed=True)


class FakeNotifier:
    def __init__(self) -> None:
        self.admin_notifications: list[tuple[AccessApplication, str | None]] = []
        self.applicant_notifications: list[AccessApplication] = []

    async def notify_admin(
        self,
        application: AccessApplication,
        username: str | None,
    ) -> None:
        self.admin_notifications.append((application, username))

    async def notify_applicant(self, application: AccessApplication) -> None:
        self.applicant_notifications.append(application)


class FailingNotifier(FakeNotifier):
    async def notify_admin(
        self,
        application: AccessApplication,
        username: str | None,
    ) -> None:
        raise ConnectionError("Telegram is unavailable")


class FakeOutbox:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, str]]] = []

    async def enqueue(self, event_type: str, payload: dict[str, str]) -> None:
        self.events.append((event_type, payload))


def test_submit_notifies_admin_only_for_new_application() -> None:
    async def scenario() -> None:
        application = AccessApplication.submit(telegram_id=42)
        repository = FakeRepository(application)
        notifier = FakeNotifier()
        submit = SubmitAccessApplication(repository, notifier)

        result = await submit.execute(telegram_id=42, username="client")

        assert result.is_new is True
        assert notifier.admin_notifications == [(application, "client")]

    import asyncio

    asyncio.run(scenario())


def test_non_admin_cannot_approve() -> None:
    async def scenario() -> None:
        application = AccessApplication.submit(telegram_id=42)
        approve = ApproveAccessApplication(
            FakeRepository(application),
            FakeNotifier(),
            admin_telegram_id=99,
        )

        with pytest.raises(ForbiddenReviewer):
            await approve.execute(application_id=application.id, reviewer_id=7)

    import asyncio

    asyncio.run(scenario())


def test_existing_submission_does_not_notify_admin_again() -> None:
    async def scenario() -> None:
        application = AccessApplication.submit(telegram_id=42)
        notifier = FakeNotifier()
        submit = SubmitAccessApplication(
            FakeRepository(application, is_new=False),
            notifier,
        )

        result = await submit.execute(telegram_id=42, username="client")

        assert result.is_new is False
        assert notifier.admin_notifications == []

    import asyncio

    asyncio.run(scenario())


def test_admin_can_reject_pending_application() -> None:
    async def scenario() -> None:
        application = AccessApplication.submit(telegram_id=42)
        reject = RejectAccessApplication(
            FakeRepository(application),
            FakeNotifier(),
            admin_telegram_id=99,
        )

        result = await reject.execute(application_id=application.id, reviewer_id=99)

        assert result.application.status is ApplicationStatus.REJECTED

    import asyncio

    asyncio.run(scenario())


def test_submit_queues_outbox_event_when_admin_notification_fails() -> None:
    async def scenario() -> None:
        application = AccessApplication.submit(telegram_id=42)
        outbox = FakeOutbox()
        submit = SubmitAccessApplication(
            FakeRepository(application),
            FailingNotifier(),
            outbox,
        )

        await submit.execute(telegram_id=42, username="client")

        assert outbox.events == [
            (
                "access_application_submitted",
                {"application_id": str(application.id), "username": "client"},
            )
        ]

    import asyncio

    asyncio.run(scenario())
