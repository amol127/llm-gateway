import httpx
from app.config import settings
from app.providers.base import Provider, ChatResult

class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)

    async def chat(self, model: str, messages: list[dict]) -> ChatResult:
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        resp = await self.client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": settings.gemini_api_key},
            json={"contents": contents},
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usageMetadata", {})
        return ChatResult(
            text=data["candidates"][0]["content"]["parts"][0]["text"],
            model=model,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
        )