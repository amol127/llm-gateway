import logging

import redis.asyncio as redis

from app.reliability import CircuitBreaker

log = logging.getLogger("gateway.redis")
breaker = CircuitBreaker(failure_threshold=3, cooldown=5.0)


async def guarded(op, default=None):
    """Run a Redis operation. If Redis is failing, skip it fast and return default."""
    if not breaker.allow():
        return default
    try:
        result = await op()
    except (redis.RedisError, OSError):
        was_open = breaker.opened_at is not None
        breaker.record_failure()
        if breaker.opened_at is not None and not was_open:
            log.error("redis circuit opened: skipping Redis for %.0fs", breaker.cooldown)
        return default
    if breaker.failures:
        log.info("redis recovered")
    breaker.record_success()
    return result