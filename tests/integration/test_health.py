import asyncio

import httpx

from app.core.config import get_settings


def test_health_endpoint_returns_no_operational_details(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BUSINESS_BOT_TOKEN", "123456789:business-token")
    monkeypatch.setenv("TELEGRAM_ACCESS_BOT_TOKEN", "123456789:access-token")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "42")
    monkeypatch.setenv(
        "TELEGRAM_ACCESS_WEBHOOK_SECRET",
        "0123456789abcdef0123456789abcdef",
    )
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
