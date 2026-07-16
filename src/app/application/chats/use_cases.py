"""Owner workflows for listing and resuming handed-off chats."""

from app.application.chats.ports import ChatManagementPort
from app.application.tenants.ports import TenantPort
from app.application.tenants.use_cases import TenantNotFound
from app.domain.chats.entities import CustomerChat


class ListOwnerHandoffChats:
    """List only the current owner's chats handed to a human."""

    def __init__(self, tenants: TenantPort, chats: ChatManagementPort) -> None:
        self._tenants = tenants
        self._chats = chats

    async def execute(self, owner_telegram_id: int) -> list[CustomerChat]:
        """Resolve the owner tenant before listing handoff chats."""
        tenant = await self._tenants.get_by_owner(owner_telegram_id)
        if tenant is None:
            raise TenantNotFound("Owner has not completed onboarding.")
        return await self._chats.list_handoff_chats(tenant.id)


class ResumeOwnerChatAI:
    """Return a selected owner chat to the AI reply mode."""

    def __init__(self, tenants: TenantPort, chats: ChatManagementPort) -> None:
        self._tenants = tenants
        self._chats = chats

    async def execute(self, owner_telegram_id: int, telegram_chat_id: int) -> bool:
        """Resume only a handed-off chat under the current owner's tenant."""
        tenant = await self._tenants.get_by_owner(owner_telegram_id)
        if tenant is None:
            raise TenantNotFound("Owner has not completed onboarding.")
        return await self._chats.resume_ai(tenant.id, telegram_chat_id)
