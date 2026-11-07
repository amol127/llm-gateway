import hashlib
import json
import logging

import redis.asyncio as redis

from app.config import settings
from app.providers.base import ChatResult

log = logging.getLogger("gateway.cache")
r = redis.from_url(settings.redis_url, decode_responses=True)


def cache_key(tenant_id: int, model: str, messages: list[dict]) -> str:
    # tenant_id is part of the key, so one customer can never read another's cached answers.
    raw = json.dumps({"model": model, "messages": messages}, sort_keys=True, separators=(",", ":"))
    return f"cache:{tenant_id}:{hashlib.sha256(raw.encode()).hexdigest()}"


async def get_cached(key: str) -> ChatResult | None:
    try:
        data = await r.get(key)
    except redis.RedisError:
        log.exception("cache read failed, treating as miss")
        return None
    return ChatResult.model_validate_json(data) if data else None


async def set_cached(key: str, result: ChatResult, ttl: int) -> None:
    try:
        await r.set(key, result.model_dump_json(), ex=ttl)
    except redis.RedisError:
        log.exception("cache write failed")


        