"""Ports for tenant-scoped owner chat controls."""

from typing import Protocol
from uuid import UUID

from app.domain.chats.entities import CustomerChat


class ChatManagementPort(Protocol):
    """List and resume chats without crossing tenant boundaries."""

    async def list_handoff_chats(
        self, tenant_id: UUID, limit: int = 10
    ) -> list[CustomerChat]:
        """Return the tenant's chats currently handled by a human."""

    async def resume_ai(self, tenant_id: UUID, telegram_chat_id: int) -> bool:
        """Resume AI only for a handed-off chat belonging to the tenant."""
