import logging
import redis.asyncio as redis
from fastapi import Depends, HTTPException, Response
from app.auth import authenticate
from app.config import settings

log = logging.getLogger("gateway.ratelimit")
r = redis.from_url(settings.redis_url, decode_responses=True)

# Runs atomically inside Redis, so concurrent requests can't race each other.
TOKEN_BUCKET = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])

local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  ts = now
end

tokens = math.min(capacity, tokens + math.max(0, now - ts) * refill)

local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end

redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(capacity / refill) * 2)
return {allowed, math.floor(tokens)}
"""
_script = r.register_script(TOKEN_BUCKET)


async def rate_limit(response: Response, tenant_id: int = Depends(authenticate)) -> int:
    try:
        allowed, remaining = await _script(
            keys=[f"rl:tenant:{tenant_id}"],
            args=[settings.rate_limit_capacity, settings.rate_limit_refill_per_sec],
        )
    except redis.RedisError:
        # Fail open: a Redis outage should not take the whole gateway down.
        log.exception("rate limiter unavailable, allowing request")
        return tenant_id

    response.headers["X-RateLimit-Remaining"] = str(remaining)
    if not allowed:
        retry_after = max(1, round(1 / settings.rate_limit_refill_per_sec))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    return tenant_id




