from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.webhooks.access import create_access_webhook_router


class FakeDispatcher:
    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []

    async def feed_raw_update(self, bot: object, update: dict[str, object]) -> None:
        self.updates.append(update)


def test_invalid_webhook_secret_returns_not_found() -> None:
    app = FastAPI()
    app.include_router(
        create_access_webhook_router(
            dispatcher=FakeDispatcher(),
            bot=object(),
            secret="secret",
        )
    )

    with TestClient(app) as client:
        response = client.post("/webhooks/access/wrong", json={"update_id": 1})

    assert response.status_code == 404


def test_valid_webhook_secret_forwards_update_to_dispatcher() -> None:
    dispatcher = FakeDispatcher()
    app = FastAPI()
    app.include_router(
        create_access_webhook_router(
            dispatcher=dispatcher,
            bot=object(),
            secret="secret",
        )
    )

    with TestClient(app) as client:
        response = client.post("/webhooks/access/secret", json={"update_id": 1})

    assert response.status_code == 204
    assert dispatcher.updates == [{"update_id": 1}]
