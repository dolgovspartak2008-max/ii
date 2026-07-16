from uuid import uuid4

import pytest

from app.application.ai.ports import AIProviderError
from app.application.ai.use_cases import (
    CLARIFICATION_TEXT,
    GREETING_TEXT,
    NEEDS_OWNER_TOKEN,
    NEEDS_REPHRASE_TOKEN,
    OUT_OF_SCOPE_TOKEN,
    OWNER_WAIT_TEXT,
    GenerateBusinessReply,
)
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
    def __init__(
        self, profile: BusinessProfile | None, ai_enabled: bool = True
    ) -> None:
        self.profile = profile
        self.ai_enabled = ai_enabled

    async def get_business_profile(self, tenant_id):
        return self.profile

    async def is_ai_enabled(self, tenant_id):
        return self.ai_enabled


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
@pytest.mark.parametrize("greeting", ["Здравствуйте", "Привет!", "Добрый день"])
async def test_short_greeting_returns_fixed_welcome_without_provider_call(
    greeting: str,
) -> None:
    tenant_id = uuid4()
    responder = FakeResponder()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        responder,
    )

    reply = await service.execute(tenant_id, 100, greeting)

    assert reply == GREETING_TEXT
    assert responder.requests == []


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


@pytest.mark.asyncio
async def test_disabled_tenant_does_not_generate_reply() -> None:
    tenant_id = uuid4()
    responder = FakeResponder()
    service = GenerateBusinessReply(
        FakeTenants(
            BusinessProfile.create("Кофейня", "Кофе с собой"), ai_enabled=False
        ),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        responder,
    )

    assert await service.execute(tenant_id, 100, "Есть капучино?") is None
    assert responder.requests == []


@pytest.mark.asyncio
async def test_uncertain_answer_becomes_clarification_request() -> None:
    tenant_id = uuid4()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        FakeResponder(NEEDS_REPHRASE_TOKEN),
    )

    reply = await service.execute(tenant_id, 100, "Непонятный вопрос")

    assert reply == CLARIFICATION_TEXT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        "ИИ: [[NEEDS_REPHRASE]]",
        "`[[NEEDS_REPHRASE]]`",
    ],
)
async def test_uncertainty_marker_variants_become_clarification(
    answer: str,
) -> None:
    tenant_id = uuid4()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        FakeResponder(answer),
    )

    reply = await service.execute(tenant_id, 100, "Непонятный вопрос")

    assert reply == CLARIFICATION_TEXT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (OUT_OF_SCOPE_TOKEN, CLARIFICATION_TEXT),
        ("ИИ: `[[OUT_OF_SCOPE]]`", CLARIFICATION_TEXT),
        (NEEDS_OWNER_TOKEN, OWNER_WAIT_TEXT),
        ("`[[NEEDS_OWNER]]`", OWNER_WAIT_TEXT),
    ],
)
async def test_intent_markers_receive_their_own_customer_safe_reply(
    answer: str,
    expected: str,
) -> None:
    tenant_id = uuid4()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        FakeResponder(answer),
    )

    reply = await service.execute(tenant_id, 100, "Вопрос клиента")

    assert reply == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        "User Safety: safe",
        "ИИ: `User Safety: unsafe`",
    ],
)
async def test_provider_safety_artifact_becomes_owner_wait_reply(
    answer: str,
) -> None:
    tenant_id = uuid4()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        FakeResponder(answer),
    )

    reply = await service.execute(tenant_id, 100, "Вопрос клиента")

    assert reply == OWNER_WAIT_TEXT
