from  fastapi import FastAPI , HTTPException, Depends
from pydantic import BaseModel
# from app.providers.anthropic import AnthropicProvider
from app.providers.mock import MockProvider
from app.reliability import AllProvidersFailed, Router
from app.auth import authenticate
import httpx

from app.ratelimit import rate_limit


app = FastAPI(title="LLM Gateway")
provider = MockProvider()





from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import httpx

from app.providers.mock import MockProvider
from app.ratelimit import rate_limit
from app.reliability import AllProvidersFailed, Router

app = FastAPI(title="LLM Gateway")

router = Router([
    MockProvider(name="flaky", failure_rate=0.5),
    MockProvider(name="reliable"),
])


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat")
async def chat(req: ChatRequest, tenant_id: int = Depends(rate_limit)):
    try:
        provider_name, result = await router.chat(req.model, req.messages)
    except AllProvidersFailed as e:
        raise HTTPException(status_code=503, detail={"errors": e.errors})
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail={"provider_status": e.response.status_code})
    return {"provider": provider_name, **result.model_dump()}


@app.get("/debug/breakers")
async def breakers():
    return {n: {"failures": b.failures, "open": b.opened_at is not None}
            for n, b in router.breakers.items()}

