import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastembed import TextEmbedding
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import SemanticEntry
from app.providers.base import ChatResult

log = logging.getLogger("gateway.semantic")
_model: TextEmbedding | None = None


def _embed_sync(text: str) -> list[float]:
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")  # 384 dims, first call downloads it
    return [float(x) for x in next(iter(_model.embed([text])))]


async def embed(text: str) -> list[float]:
    # CPU-bound, so run it off the event loop
    return await asyncio.to_thread(_embed_sync, text)


def _prompt(messages: list[dict]) -> str | None:
    if len(messages) == 1 and messages[0].get("role") == "user":
        return str(messages[0].get("content", ""))
    return None


async def semantic_lookup(tenant_id: int, model: str, messages: list[dict]):
    """Returns (ChatResult, similarity) or None. Never raises."""
    prompt = _prompt(messages)
    if not prompt:
        return None
    try:
        vec = await embed(prompt)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.cache_ttl_seconds)
        dist = SemanticEntry.embedding.cosine_distance(vec)
        async with SessionLocal() as s:
            row = (await s.execute(
                select(SemanticEntry, dist.label("d"))
                .where(SemanticEntry.tenant_id == tenant_id,
                       SemanticEntry.model == model,
                       SemanticEntry.created_at > cutoff)
                .order_by(dist).limit(1)
            )).first()
        if row is None:
            return None
        entry, d = row
        similarity = 1 - float(d)
        if similarity < settings.semantic_threshold:
            return None
        return ChatResult.model_validate_json(entry.response_json), similarity
    except Exception:
        log.exception("semantic lookup failed, treating as miss")
        return None


async def semantic_store(tenant_id: int, model: str, messages: list[dict], result: ChatResult):
    prompt = _prompt(messages)
    if not prompt:
        return
    try:
        vec = await embed(prompt)
        async with SessionLocal() as s:
            s.add(SemanticEntry(tenant_id=tenant_id, model=model, prompt=prompt,
                                embedding=vec, response_json=result.model_dump_json()))
            await s.commit()
    except Exception:
        log.exception("semantic store failed")