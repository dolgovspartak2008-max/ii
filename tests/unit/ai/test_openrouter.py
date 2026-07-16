import json
from uuid import uuid4

import httpx
import pytest

from app.infrastructure.ai.openrouter import LLMProviderError, OpenRouterAIResponder


@pytest.mark.asyncio
async def test_openrouter_sends_tenant_business_context_and_extracts_answer() -> None:
    received: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        received["authorization"] = request.headers["Authorization"]
        received["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  Запись доступна.  "}}]},
        )

    responder = OpenRouterAIResponder(
        api_key="test-key",
        model="openrouter/auto",
        transport=httpx.MockTransport(handler),
    )

    reply = await responder.generate(
        uuid4(), "Студия", "Стрижки и окрашивание", "Можно записаться сегодня?"
    )

    assert reply == "Запись доступна."
    assert received["authorization"] == "Bearer test-key"
    payload = received["payload"]
    assert payload["model"] == "openrouter/auto"
    assert payload["temperature"] == 0.2
    system_prompt = payload["messages"][0]["content"]
    assert "приветствие" in system_prompt
    assert "[[OUT_OF_SCOPE]]" in system_prompt
    assert "[[NEEDS_OWNER]]" in system_prompt
    assert "грамматически правильном русском языке" in system_prompt
    assert "пробелы между словами" in system_prompt
    assert "прямой вопрос клиента" in system_prompt
    assert "Не называй цены" in system_prompt
    assert "User Safety" in system_prompt
    assert "Студия" in payload["messages"][0]["content"]
    assert payload["messages"][1] == {
        "role": "user",
        "content": "Можно записаться сегодня?",
    }


@pytest.mark.asyncio
async def test_openrouter_raises_provider_error_for_invalid_response() -> None:
    responder = OpenRouterAIResponder(
        api_key="test-key",
        model="openrouter/auto",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    )

    with pytest.raises(LLMProviderError):
        await responder.generate(uuid4(), "Студия", "Стрижки", "Цена?")
