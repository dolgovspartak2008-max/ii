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
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты ассистент бизнеса. Бизнес: "
                        f"{business_name}. Описание: {business_description}. "
                        "На приветствие или обычное начало разговора отвечай коротко и "
                        "дружелюбно, предложи задать вопрос о бизнесе. "
                        "Если вопрос явно не связан с этим бизнесом, верни только "
                        "[[OUT_OF_SCOPE]]. Если вопрос может быть связан с бизнесом, "
                        "но в описании недостаточно точных данных для ответа, верни "
                        "только [[NEEDS_OWNER]]. Во всех остальных случаях отвечай "
                        "только по известной информации о бизнесе. Не придумывай факты."
                        " Пиши на грамматически правильном русском языке. Перед "
                        "отправкой проверь согласование слов, орфографию, "
                        "пунктуацию и пробелы между словами. Отвечай только на "
                        "прямой вопрос клиента: не пересказывай без запроса весь "
                        "ассортимент и не добавляй шаблонный вопрос в конце ответа."
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
