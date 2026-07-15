import pytest

from app.domain.access.entities import (
    AccessApplication,
    ApplicationStatus,
    InvalidApplicationTransition,
)


def test_pending_application_can_be_approved() -> None:
    application = AccessApplication.submit(telegram_id=42)

    application.approve()

    assert application.status is ApplicationStatus.APPROVED


def test_approved_application_cannot_be_rejected() -> None:
    application = AccessApplication.submit(telegram_id=42)
    application.approve()

    with pytest.raises(InvalidApplicationTransition):
        application.reject()
