
import time
import httpx
import asyncio
import logging
from fastapi import FastAPI , HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from contextlib import asynccontextmanager

from app.timing import summary


from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


from app.models import RequestLog
from app.cache import get_cached, set_cached, cache_key
from app.config import settings
from app.db import Base, engine, get_session

# from app.providers.anthropic import AnthropicProvider
from app.auth import authenticate
from app.guardrails import apply_guardrails
from app.providers.mock import MockProvider
from app.pricing import cost_usd
from app.timing import timed
from app.tracing import  log_writer,  enqueue_request
from app.ratelimit import rate_limit
from app.reliability import AllProvidersFailed, Router, UnknownModel
from app.routing import build_router




log = logging.getLogger("gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(log_writer())
    yield
    task.cancel()


app = FastAPI(title="LLM Gateway", lifespan=lifespan)
provider = MockProvider()




# router = Router([
#     MockProvider(name="flaky", failure_rate=0.5),
#     MockProvider(name="reliable"),
# ])

router = build_router()

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]

def _ms(start:float) -> int:
    return int((time.perf_counter()-start)*1000)



@app.get("/health")
async def health():
    return {"status": "ok"}



@app.post("/v1/chat")
async def chat(
    req: ChatRequest,
    background: BackgroundTasks,
    tenant_id: int = Depends(rate_limit),
):
    start = time.perf_counter()

    messages, pii = req.messages, {}
    if settings.pii_mode != "off":
        messages, pii = apply_guardrails(req.messages)
        if pii:
            log.warning("pii detected tenant=%s types=%s", tenant_id, pii)  # counts only
            if settings.pii_mode == "block":
                raise HTTPException(
                    status_code=400,
                    detail={"error": "pii_detected", "types": sorted(pii)},
                )

    key = cache_key(tenant_id, req.model, messages)  # masked messages, never raw
    with timed("cache_get"):
        cached = await get_cached(key)

    if cached:
        enqueue_request(
            tenant_id=tenant_id, provider="cache", model=req.model,
            input_tokens=0, output_tokens=0, cost_usd=0,
            saved_usd=cost_usd(cached.model, cached.input_tokens, cached.output_tokens),
            latency_ms=_ms(start), status="ok", cached=True,
        )
        return {"provider": "cache", "cached": True, **cached.model_dump()}

    # Semantic cache removed from the hot path (not built yet, and it was unmeasured).

    try:
        with timed("router"):
            provider_name, result = await router.chat(req.model, messages)
    except UnknownModel:
        raise HTTPException(status_code=400, detail={"error": "unknown_model", "model": req.model})
    except AllProvidersFailed as e:
        enqueue_request(
            tenant_id=tenant_id, model=req.model, latency_ms=_ms(start),
            status="error", error="; ".join(e.errors)[:500],
        )
        raise HTTPException(status_code=503, detail={"errors": e.errors})
    except httpx.HTTPStatusError as e:
        enqueue_request(
            tenant_id=tenant_id, model=req.model, latency_ms=_ms(start),
            status="error", error=f"provider_status {e.response.status_code}",
        )
        raise HTTPException(status_code=502, detail={"provider_status": e.response.status_code})
    except Exception:
        log.exception("unhandled error tenant=%s model=%s", tenant_id, req.model)
        enqueue_request(
            tenant_id=tenant_id, model=req.model, latency_ms=_ms(start),
            status="error", error="internal_error",
        )
        raise HTTPException(status_code=502, detail={"error": "upstream_failure"})

    enqueue_request(
        tenant_id=tenant_id,
        provider=provider_name,
        model=req.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=cost_usd(result.model, result.input_tokens, result.output_tokens),
        latency_ms=_ms(start),
        status="ok",
    )
    background.add_task(set_cached, key, result, settings.cache_ttl_seconds)
    return {"provider": provider_name, **result.model_dump()}



@app.get("/usage")
async def usage(
    tenant_id: int = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    q = select(
        func.count(RequestLog.id),                                           # n
        func.coalesce(func.sum(RequestLog.input_tokens), 0),                 # tin
        func.coalesce(func.sum(RequestLog.output_tokens), 0),                # tout
        func.coalesce(func.sum(RequestLog.cost_usd), 0),                     # cost
        func.coalesce(func.avg(RequestLog.latency_ms), 0),                   # avg_ms
        func.count(RequestLog.id).filter(RequestLog.status == "error"),      # errors
        func.count(RequestLog.id).filter(RequestLog.cached.is_(True)),       # hits
        func.coalesce(func.sum(RequestLog.saved_usd), 0),                    # saved
    ).where(RequestLog.tenant_id == tenant_id)
    n, tin, tout, cost, avg_ms, errors, hits, saved = (await session.execute(q)).one()
    return {
        "requests": n,
        "errors": errors,
        "input_tokens": int(tin),
        "output_tokens": int(tout),
        "cost_usd": round(float(cost), 6),
        "avg_latency_ms": round(float(avg_ms), 1),
        "cache_hits": hits,
        "cache_hit_rate": round(hits / n, 3) if n else 0,
        "saved_usd": round(float(saved), 6),
    }


@app.get("/debug/timings")
async def timings(tenant_id: int = Depends(authenticate)):
    if not settings.timing_enabled:
        return {"enabled": False, "hint": "set TIMING_ENABLED=true and restart"}
    return summary()



@app.get("/debug/breakers")
async def breakers():
    return {n: {"failures": b.failures, "open": b.opened_at is not None}
            for n, b in router.breakers.items()}





# curl -s -X POST localhost:8000/v1/chat -H "Authorization: Bearer gw_lUDynOcB3cqFKNE79XdP2wOBeYgqdF-Wh1G1_rTcAEI" -H "content-type: application/json" -d "{\"model\":\"m\",\"messages\":[{\"role\":\"user\",\"content\":\"What is a rate limiter?\"}]}"
# curl -s -X POST localhost:8000/v1/chat -H "Authorization: Bearer gw_lUDynOcB3cqFKNE79XdP2wOBeYgqdF-Wh1G1_rTcAEI" -H "content-type: application/json" -d "{\"model\":\"m\",\"messages\":[{\"role\":\"user\",\"content\":\"Explain what a rate limiter is\"}]}"
# curl -s -X POST localhost:8000/v1/chat -H "Authorization: Bearer gw_lUDynOcB3cqFKNE79XdP2wOBeYgqdF-Wh1G1_rTcAEI" -H "content-type: application/json" -d "{\"model\":\"m\",\"messages\":[{\"role\":\"user\",\"content\":\"How do I bake bread?\"}]}"



