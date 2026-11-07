import httpx
from app.config import settings
from app.providers.base import Provider, ChatResult

class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)

    async def chat(self, model: str, messages: list[dict]) -> ChatResult:
        resp = await self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "max_tokens": 1000, "messages": messages},
        )
        resp.raise_for_status()
        data = resp.json()
        return ChatResult(
            text=data["content"][0]["text"],
            model=data["model"],
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"],
        )