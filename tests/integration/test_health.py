import asyncio

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings


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


def test_main_passes_configured_owner_to_onboarding(monkeypatch) -> None:
    import app.main as main_module

    captured_owner_ids: list[int | None] = []

    class CapturingOnboarding:
        def __init__(self, approvals, tenants, direct_owner_telegram_id=None) -> None:
            captured_owner_ids.append(direct_owner_telegram_id)

    settings = Settings(
        public_base_url="https://example.amvera.tech",
        telegram_business_bot_token="123456789:business-token",
        telegram_access_bot_token="123456789:access-token",
        admin_telegram_id=42,
        telegram_access_webhook_secret="0123456789abcdef0123456789abcdef",
        telegram_business_webhook_secret="abcdef0123456789abcdef0123456789",
        openrouter_api_key="openrouter-key",
        openrouter_model="openrouter/auto",
    )
    monkeypatch.setattr(main_module, "OnboardApprovedOwner", CapturingOnboarding)

    main_module.create_app(settings)

    assert captured_owner_ids == [42]


def test_main_registers_access_review_in_business_bot_dispatcher(monkeypatch) -> None:
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

    dispatchers = []

    class CapturingDispatcher:
        def __init__(self) -> None:
            self.router_names: list[str] = []
            dispatchers.append(self)

        def include_router(self, router) -> None:
            self.router_names.append(router.name)

    settings = Settings(
        public_base_url="https://example.amvera.tech",
        telegram_business_bot_token="123456789:business-token",
        telegram_access_bot_token="123456789:access-token",
        admin_telegram_id=42,
        telegram_access_webhook_secret="0123456789abcdef0123456789abcdef",
        telegram_business_webhook_secret="abcdef0123456789abcdef0123456789",
        openrouter_api_key="openrouter-key",
        openrouter_model="openrouter/auto",
    )
    monkeypatch.setattr(main_module, "Dispatcher", CapturingDispatcher)

    main_module.create_app(settings)

    assert dispatchers[0].router_names == ["access-application"]
    assert "access-review" in dispatchers[1].router_names
