"""Protected webhook endpoint for the main Telegram Business bot."""

import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from app.presentation.webhooks.access import AccessUpdateDispatcher


def create_business_webhook_router(
    dispatcher: AccessUpdateDispatcher,
    bot: Any,
    secret: str,
) -> APIRouter:
    """Create a distinct secret-protected endpoint for main-bot updates."""
    router = APIRouter()

    @router.post("/webhooks/business/{provided_secret}", status_code=204)
    async def receive_business_update(
        provided_secret: str,
        update: dict[str, object],
    ) -> Response:
        if not secrets.compare_digest(provided_secret, secret):
            raise HTTPException(status_code=404)
        await dispatcher.feed_raw_update(bot, update)
        return Response(status_code=204)

    return router
