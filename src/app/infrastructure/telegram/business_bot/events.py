"""Official Telegram Business event handlers."""

from aiogram import Router
from aiogram.types import BusinessConnection, Message

from app.infrastructure.persistence.repositories.chats import (
    PostgresBusinessChatRepository,
)
from app.infrastructure.persistence.repositories.tenants import PostgresTenantRepository


def is_owner_message(owner_telegram_id: int, sender_telegram_id: int | None) -> bool:
    """Return whether a Business message was written by the tenant owner."""
    return sender_telegram_id == owner_telegram_id


def create_business_events_router(
    tenants: PostgresTenantRepository,
    chats: PostgresBusinessChatRepository,
) -> Router:
    """Persist connections and stop AI when the owner takes a chat over."""
    router = Router(name="business-chat-events")

    @router.business_connection()
    async def save_connection(connection: BusinessConnection) -> None:
        tenant = await tenants.get_by_owner(connection.user.id)
        if tenant is None:
            return
        await chats.upsert_connection(
            connection.id,
            tenant.id,
            connection.user.id,
            connection.is_enabled,
        )

    @router.business_message()
    async def handle_business_message(message: Message) -> None:
        if message.business_connection_id is None:
            return
        connection = await chats.get_connection(message.business_connection_id)
        if connection is None or not connection.is_enabled:
            return
        sender_id = message.from_user.id if message.from_user is not None else None
        await chats.open_customer_chat(connection.tenant_id, message.chat.id)
        if is_owner_message(connection.owner_telegram_id, sender_id):
            await chats.mark_human_handoff(connection.tenant_id, message.chat.id)

    return router
