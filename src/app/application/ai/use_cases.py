"""Rules controlling when an AI reply may be generated."""

from uuid import UUID

from app.application.ai.ports import AIProviderError, AIResponder
from app.domain.chats.entities import ChatState
from app.infrastructure.persistence.repositories.chats import (
    PostgresBusinessChatRepository,
)
from app.infrastructure.persistence.repositories.tenants import PostgresTenantRepository

OUT_OF_SCOPE_TOKEN = "[[OUT_OF_SCOPE]]"
NEEDS_REPHRASE_TOKEN = "[[NEEDS_REPHRASE]]"
NEEDS_OWNER_TOKEN = "[[NEEDS_OWNER]]"
CLARIFICATION_TEXT = (
    "Извините, я не понял вопрос. Пожалуйста, переформулируйте его "
    "или уточните детали."
)
OWNER_WAIT_TEXT = (
    "Этот вопрос может требовать уточнения у владельца или консультанта. "
    "Пожалуйста, дождитесь их ответа, чтобы получить более точную консультацию."
)
GREETING_TEXT = "Здравствуйте! Чем могу помочь по вопросам нашего бизнеса?"
SHORT_GREETINGS = frozenset(
    {"здравствуйте", "здраствуйте", "привет", "добрый день", "добрый вечер"}
)


def normalize_reserved_response(answer: str) -> str:
    """Normalize a reserved provider marker despite harmless formatting."""
    normalized = answer.strip()
    if normalized.startswith("ИИ:"):
        normalized = normalized.removeprefix("ИИ:").strip()
    if normalized.startswith("`") and normalized.endswith("`"):
        normalized = normalized[1:-1].strip()
    return normalized


def is_short_greeting(customer_text: str) -> bool:
    """Recognize a standalone greeting without delegating it to the provider."""
    normalized = " ".join(customer_text.lower().split()).rstrip("!?. ,")
    return normalized in SHORT_GREETINGS


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
        if is_short_greeting(customer_text):
            return GREETING_TEXT
        try:
            answer = (await self._responder.generate(
                tenant_id, profile.name, profile.description, customer_text
            )).strip()
        except AIProviderError:
            return None
        if not answer:
            return None
        marker = normalize_reserved_response(answer)
        if marker == NEEDS_OWNER_TOKEN:
            return OWNER_WAIT_TEXT
        if marker in {NEEDS_REPHRASE_TOKEN, OUT_OF_SCOPE_TOKEN}:
            return CLARIFICATION_TEXT
        return answer if answer.startswith("ИИ:") else f"ИИ: {answer}"
