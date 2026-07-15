from uuid import uuid4

import pytest

from app.application.ai.ports import AIProviderError
from app.application.ai.use_cases import GenerateBusinessReply
from app.domain.chats.entities import ChatState, CustomerChat
from app.domain.tenants.entities import BusinessProfile


class FakeChats:
    def __init__(self, chat: CustomerChat | None) -> None:
        self.chat = chat

    async def get_customer_chat(self, tenant_id, telegram_chat_id):
        if self.chat is not None and self.chat.tenant_id == tenant_id:
            return self.chat
        return None


class FakeTenants:
    def __init__(self, profile: BusinessProfile | None) -> None:
        self.profile = profile

    async def get_business_profile(self, tenant_id):
        return self.profile


class FakeResponder:
    def __init__(self, answer: str = "Добрый день!") -> None:
        self.answer = answer
        self.requests: list[tuple] = []

    async def generate(
        self, tenant_id, business_name, business_description, customer_text
    ):
        self.requests.append(
            (tenant_id, business_name, business_description, customer_text)
        )
        return self.answer


class UnavailableResponder:
    async def generate(
        self, tenant_id, business_name, business_description, customer_text
    ):
        raise AIProviderError("Provider unavailable")


@pytest.mark.asyncio
async def test_active_chat_generates_tenant_scoped_prefixed_reply() -> None:
    tenant_id = uuid4()
    responder = FakeResponder("Ремонт займёт один день.")
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Автосервис", "Ремонт автомобилей")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        responder,
    )

    reply = await service.execute(tenant_id, 100, "Сколько длится ремонт?")

    assert reply == "ИИ: Ремонт займёт один день."
    assert responder.requests == [
        (tenant_id, "Автосервис", "Ремонт автомобилей", "Сколько длится ремонт?")
    ]


@pytest.mark.asyncio
async def test_handoff_chat_does_not_generate_reply() -> None:
    tenant_id = uuid4()
    responder = FakeResponder()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.HUMAN_HANDOFF)),
        responder,
    )

    reply = await service.execute(tenant_id, 100, "Есть капучино?")

    assert reply is None
    assert responder.requests == []


@pytest.mark.asyncio
async def test_missing_profile_does_not_generate_reply() -> None:
    tenant_id = uuid4()
    responder = FakeResponder()
    service = GenerateBusinessReply(
        FakeTenants(None),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        responder,
    )

    assert await service.execute(tenant_id, 100, "Здравствуйте") is None
    assert responder.requests == []


@pytest.mark.asyncio
async def test_provider_failure_does_not_generate_customer_reply() -> None:
    tenant_id = uuid4()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        UnavailableResponder(),
    )

    assert await service.execute(tenant_id, 100, "Есть капучино?") is None
