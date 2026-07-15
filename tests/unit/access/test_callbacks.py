from uuid import uuid4

from app.infrastructure.telegram.access_bot.callbacks import AccessReviewCallback


def test_access_review_callback_round_trip() -> None:
    application_id = uuid4()

    parsed = AccessReviewCallback.unpack(
        AccessReviewCallback(action="approve", application_id=application_id).pack()
    )

    assert parsed.action == "approve"
    assert parsed.application_id == application_id
