"""Rules controlling when an AI reply may be generated."""

from uuid import UUID

from app.application.ai.ports import AIProviderError, AIResponder
from app.domain.chats.entities import ChatState
from app.infrastructure.persistence.repositories.chats import (
    PostgresBusinessChatRepository,
)
from app.infrastructure.persistence.repositories.tenants import PostgresTenantRepository

NEEDS_REPHRASE_TOKEN = "[[NEEDS_REPHRASE]]"
CLARIFICATION_TEXT = (
    "Извините, я не понял вопрос. Пожалуйста, переформулируйте его "
    "или уточните детали."
)


class GenerateBusinessReply:
    """Generate a reply only for an active chat with tenant business context."""

    def __init__(
        self,
        tenants: PostgresTenantRepository,
        chats: PostgresBusinessChatRepository,
        responder: AIResponder,
    ) -> None:
        self._tenants = tenants
        self._chats = chats
        self._responder = responder

    async def execute(
        self, tenant_id: UUID, telegram_chat_id: int, customer_text: str
    ) -> str | None:
        chat = await self._chats.get_customer_chat(tenant_id, telegram_chat_id)
        if chat is None or chat.state is not ChatState.ACTIVE:
            return None
        if not await self._tenants.is_ai_enabled(tenant_id):
            return None
        profile = await self._tenants.get_business_profile(tenant_id)
        if profile is None:
            return None
        try:
            answer = (await self._responder.generate(
                tenant_id, profile.name, profile.description, customer_text
            )).strip()
        except AIProviderError:
            return None
        if not answer:
            return None
        if answer == NEEDS_REPHRASE_TOKEN:
            return CLARIFICATION_TEXT
        return answer if answer.startswith("ИИ:") else f"ИИ: {answer}"
