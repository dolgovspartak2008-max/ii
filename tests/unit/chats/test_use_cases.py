from uuid import uuid4

import pytest

from app.domain.chats.entities import ChatState, CustomerChat
from app.domain.tenants.entities import Tenant


class FakeTenants:
    def __init__(self, tenant: Tenant | None) -> None:
        self.tenant = tenant
        self.requested_owner_ids: list[int] = []

    async def get_by_owner(self, owner_telegram_id: int) -> Tenant | None:
        self.requested_owner_ids.append(owner_telegram_id)
        return self.tenant


class FakeChats:
    def __init__(self, handoffs: list[CustomerChat], resumed: bool = False) -> None:
        self.handoffs = handoffs
        self.resumed = resumed
        self.listed_tenant_ids = []
        self.resume_requests = []

    async def list_handoff_chats(self, tenant_id, limit: int = 10):
        self.listed_tenant_ids.append((tenant_id, limit))
        return [chat for chat in self.handoffs if chat.tenant_id == tenant_id]

    async def resume_ai(self, tenant_id, telegram_chat_id: int) -> bool:
        self.resume_requests.append((tenant_id, telegram_chat_id))
        return self.resumed


@pytest.mark.asyncio
async def test_owner_lists_only_own_handoff_chats() -> None:
    from app.application.chats.use_cases import ListOwnerHandoffChats

    tenant = Tenant.create(42)
    chats = FakeChats(
        [
            CustomerChat(tenant.id, 700, ChatState.HUMAN_HANDOFF),
            CustomerChat(uuid4(), 701, ChatState.HUMAN_HANDOFF),
        ]
    )

    result = await ListOwnerHandoffChats(FakeTenants(tenant), chats).execute(42)

    assert result == [CustomerChat(tenant.id, 700, ChatState.HUMAN_HANDOFF)]
    assert chats.listed_tenant_ids == [(tenant.id, 10)]


@pytest.mark.asyncio
async def test_owner_can_resume_only_a_chat_in_own_tenant() -> None:
    from app.application.chats.use_cases import ResumeOwnerChatAI

    tenant = Tenant.create(42)
    chats = FakeChats([], resumed=False)

    resumed = await ResumeOwnerChatAI(FakeTenants(tenant), chats).execute(42, 700)

    assert resumed is False
    assert chats.resume_requests == [(tenant.id, 700)]


@pytest.mark.asyncio
async def test_missing_owner_tenant_is_rejected() -> None:
    from app.application.chats.use_cases import ListOwnerHandoffChats
    from app.application.tenants.use_cases import TenantNotFound

    with pytest.raises(TenantNotFound):
        await ListOwnerHandoffChats(FakeTenants(None), FakeChats([])).execute(42)
