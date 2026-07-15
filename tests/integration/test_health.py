import asyncio

import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_health_endpoint_returns_no_operational_details(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BUSINESS_BOT_TOKEN", "123456789:business-token")
    monkeypatch.setenv("TELEGRAM_ACCESS_BOT_TOKEN", "123456789:access-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "42")
    monkeypatch.setenv(
        "TELEGRAM_ACCESS_WEBHOOK_SECRET",
        "0123456789abcdef0123456789abcdef",
    )
    monkeypatch.setenv(
        "TELEGRAM_BUSINESS_WEBHOOK_SECRET",
        "abcdef0123456789abcdef0123456789",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/auto")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.amvera.tech")
    get_settings.cache_clear()

    from app.main import create_app

    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/healthz")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_main_app_declares_separate_business_webhook(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BUSINESS_BOT_TOKEN", "123456789:business-token")
    monkeypatch.setenv("TELEGRAM_ACCESS_BOT_TOKEN", "123456789:access-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "42")
    monkeypatch.setenv(
        "TELEGRAM_ACCESS_WEBHOOK_SECRET",
        "0123456789abcdef0123456789abcdef",
    )
    monkeypatch.setenv(
        "TELEGRAM_BUSINESS_WEBHOOK_SECRET",
        "abcdef0123456789abcdef0123456789",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/auto")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.amvera.tech")
    get_settings.cache_clear()

    import app.main as main_module

    async def disable_webhook_registration(*args) -> None:
        return None

    monkeypatch.setattr(
        main_module,
        "configure_telegram_webhooks",
        disable_webhook_registration,
    )

    with TestClient(main_module.create_app()) as client:
        response = client.post(
            "/webhooks/business/abcdef0123456789abcdef0123456789",
            json={"update_id": 1},
        )

    assert response.status_code == 204
