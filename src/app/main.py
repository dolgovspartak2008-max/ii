"""ASGI application entry point."""

from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from fastapi import FastAPI

from app.application.access.use_cases import (
    ApproveAccessApplication,
    RejectAccessApplication,
    SubmitAccessApplication,
)
from app.application.ai.use_cases import GenerateBusinessReply
from app.application.tenants.use_cases import (
    OnboardApprovedOwner,
    UpdateBusinessProfile,
)
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.infrastructure.ai.openrouter import OpenRouterAIResponder
from app.infrastructure.persistence.repositories.access import (
    PostgresAccessApplicationRepository,
)
from app.infrastructure.persistence.repositories.chats import (
    PostgresBusinessChatRepository,
)
from app.infrastructure.persistence.repositories.outbox import (
    PostgresAccessOutboxRepository,
)
from app.infrastructure.persistence.repositories.tenants import PostgresTenantRepository
from app.infrastructure.persistence.session import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.telegram.access_bot.notifier import AiogramAccessNotifier
from app.infrastructure.telegram.access_bot.router import create_access_router
from app.infrastructure.telegram.business_bot.events import (
    create_business_events_router,
)
from app.infrastructure.telegram.business_bot.router import create_business_router
from app.presentation.webhooks.access import create_access_webhook_router
from app.presentation.webhooks.business import create_business_webhook_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    repository = PostgresAccessApplicationRepository(session_factory)
    tenants = PostgresTenantRepository(session_factory)
    chats = PostgresBusinessChatRepository(session_factory)
    outbox = PostgresAccessOutboxRepository(session_factory)
    access_bot = Bot(token=settings.telegram_access_bot_token.get_secret_value())
    notifier = AiogramAccessNotifier(access_bot, settings.admin_telegram_id)
    submit = SubmitAccessApplication(repository, notifier, outbox)
    approve = ApproveAccessApplication(
        repository,
        notifier,
        settings.admin_telegram_id,
        outbox,
    )
    reject = RejectAccessApplication(
        repository,
        notifier,
        settings.admin_telegram_id,
        outbox,
    )
    access_dispatcher = Dispatcher()
    access_dispatcher.include_router(create_access_router(submit, approve, reject))

    business_bot = Bot(token=settings.telegram_business_bot_token.get_secret_value())
    responder = OpenRouterAIResponder(
        settings.openrouter_api_key.get_secret_value(),
        settings.openrouter_model,
    )
    replies = GenerateBusinessReply(tenants, chats, responder)
    business_dispatcher = Dispatcher()
    business_dispatcher.include_router(
        create_business_router(
            OnboardApprovedOwner(repository, tenants),
            UpdateBusinessProfile(tenants),
        )
    )
    business_dispatcher.include_router(
        create_business_events_router(tenants, chats, replies, business_bot)
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await access_bot.session.close()
        await business_bot.session.close()
        await engine.dispose()

    app = FastAPI(
        title="Telegram AI SaaS",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(
        create_access_webhook_router(
            access_dispatcher,
            access_bot,
            settings.telegram_access_webhook_secret.get_secret_value(),
        )
    )
    app.include_router(
        create_business_webhook_router(
            business_dispatcher,
            business_bot,
            settings.telegram_business_webhook_secret.get_secret_value(),
        )
    )

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
