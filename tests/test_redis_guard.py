import asyncio

import redis.asyncio as redis

from app.redis_guard import breaker, guarded


def test_guard_skips_redis_after_repeated_failures():
    breaker.failures, breaker.opened_at = 0, None
    calls = 0

    async def failing():
        nonlocal calls
        calls += 1
        raise redis.ConnectionError("down")

    async def run():
        for _ in range(10):
            await guarded(failing)

    asyncio.run(run())
    assert calls == 3  # the circuit opened after 3 failures, so 7 calls were skipped