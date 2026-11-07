import asyncio
from app.providers.base import Provider, ChatResult

class MockProvider(Provider):
    name = "mock"

    async def chat(self, model: str, messages: list[dict]) -> ChatResult:
        await asyncio.sleep(0.2)  # simulate latency
        return ChatResult(
            text=f"mock reply to: {messages[-1]['content']}",
            model=model, input_tokens=10, output_tokens=8,
        )