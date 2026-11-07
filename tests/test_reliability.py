import asyncio
from app.providers.mock import MockProvider
from app.reliability import Router

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