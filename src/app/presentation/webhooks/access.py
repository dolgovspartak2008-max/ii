"""Protected webhook endpoint for the access bot."""

import secrets
from typing import Any, Protocol

from fastapi import APIRouter, HTTPException, Response


class AccessUpdateDispatcher(Protocol):
    """Minimal dispatcher interface used by the webhook adapter."""

    async def feed_raw_update(self, bot: Any, update: dict[str, object]) -> None:
        """Process a raw Telegram update."""


def create_access_webhook_router(
    dispatcher: AccessUpdateDispatcher,
    bot: Any,
    secret: str,
) -> APIRouter:
    """Create the secret-protected access bot webhook route."""
    router = APIRouter()

    @router.post("/webhooks/access/{provided_secret}", status_code=204)
    async def receive_access_update(
        provided_secret: str,
        update: dict[str, object],
    ) -> Response:
        if not secrets.compare_digest(provided_secret, secret):
            raise HTTPException(status_code=404)
        await dispatcher.feed_raw_update(bot, update)
        return Response(status_code=204)

    return router
