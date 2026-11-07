import asyncio
import random
import httpx
from app.providers.base import Provider, ChatResult

class MockProvider(Provider):

    def __init__(self, name : str = "mock", latency: float = 0.2, failure_rate: float = 0.0):
        self.name = name
        self.latency = latency
        self.failure_rate = failure_rate

    async def chat(self, model: str, messages: list[dict]) -> ChatResult:
        await asyncio.sleep(self.latency)
        if random.random() < self.failure_rate:
            raise httpx.TimeoutException("mock provider timeout")
        return ChatResult(
            text=f"mock reply to: {messages[-1]['content']}",
            model=model,
            input_tokens=10,
            output_tokens=8,
        )