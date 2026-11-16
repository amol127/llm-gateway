import asyncio
import pytest
from app.providers.mock import MockProvider
from app.reliability import Router
from app.reliability import UnknownModel


MSG = [{"role": "user", "content": "hi"}]

def test_fallback_to_second_provider():
    r = Router(
        [MockProvider(name="bad", failure_rate=1.0, latency=0),
         MockProvider(name="good", latency=0)],
        base_delay=0,
    )
    name, _ = asyncio.run(r.chat("m", MSG))
    assert name == "good"


def test_circuit_opens_after_repeated_failures():
    r = Router(
        [MockProvider(name="bad", failure_rate=1.0, latency=0),
         MockProvider(name="good", latency=0)],
        max_retries=0, base_delay=0,
    )
    for _ in range(5):
        asyncio.run(r.chat("m", MSG))
    assert r.breakers["bad"].opened_at is not None




def test_alias_routes_to_provider_model():
    seen = {}
    class Spy(MockProvider):
        async def chat(self, model, messages):
            seen["model"] = model
            return await super().chat(model, messages)
    r = Router([Spy(name="p", latency=0)], routes={"fast": [("p", "real-model-1")]})
    asyncio.run(r.chat("fast", MSG))
    assert seen["model"] == "real-model-1"

def test_unknown_alias_rejected():
    r = Router([MockProvider(name="p", latency=0)], routes={"fast": [("p", "x")]})
    with pytest.raises(UnknownModel):
        asyncio.run(r.chat("nope", MSG))