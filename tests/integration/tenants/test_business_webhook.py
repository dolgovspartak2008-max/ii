from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.webhooks.business import create_business_webhook_router


class FakeDispatcher:
    async def feed_raw_update(self, bot: object, update: dict[str, object]) -> None:
        return None


def test_business_webhook_does_not_accept_access_secret() -> None:
    app = FastAPI()
    app.include_router(
        create_business_webhook_router(
            dispatcher=FakeDispatcher(),
            bot=object(),
            secret="business-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/business/access-secret", json={"update_id": 1}
        )

    assert response.status_code == 404
