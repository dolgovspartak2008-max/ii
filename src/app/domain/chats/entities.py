"""State for chats served by a Telegram Business connection."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ChatState(StrEnum):
    """Whether AI may reply in a customer chat."""

    ACTIVE = "active"
    HUMAN_HANDOFF = "human_handoff"


@dataclass(frozen=True)
class BusinessConnection:
    """Official connection of the main bot to one tenant's business account."""

    connection_id: str
    tenant_id: UUID
    owner_telegram_id: int
    is_enabled: bool


@dataclass(frozen=True)
class CustomerChat:
    """A tenant-scoped customer chat and its reply mode."""

    tenant_id: UUID
    telegram_chat_id: int
    state: ChatState
