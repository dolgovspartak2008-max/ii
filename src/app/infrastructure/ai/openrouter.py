"""OpenAI-compatible OpenRouter adapter."""

from typing import Any
from uuid import UUID

import httpx

from app.application.ai.ports import AIProviderError


class LLMProviderError(AIProviderError):
    """Raised when the configured AI provider cannot produce an answer."""


class OpenRouterAIResponder:
    """Generate tenant-isolated replies through the OpenRouter API."""

    _base_url = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._transport = transport

    async def generate(
        self,
        tenant_id: UUID,
        business_name: str,
        business_description: str,
        customer_text: str,
    ) -> str:
        del tenant_id
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты ассистент бизнеса. Отвечай только по информации "
                        f"этого бизнеса: {business_name}. Описание: "
                        f"{business_description}. Если вопрос непонятен, не относится "
                        "к бизнесу или в описании нет ответа, верни только "
                        "[[NEEDS_REPHRASE]]. Не придумывай факты."
                    ),
                },
                {"role": "user", "content": customer_text},
            ],
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=20.0,
                transport=self._transport,
            ) as client:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
                return self._extract_content(response.json())
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise LLMProviderError(
                "OpenRouter did not return a usable answer."
            ) from error

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter returned an empty answer.")
        return content.strip()
