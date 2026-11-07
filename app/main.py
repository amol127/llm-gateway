from  fastapi import FastAPI , HTTPException
from pydantic import BaseModel
# from app.providers.anthropic import AnthropicProvider
from app.providers.mock import MockProvider
import httpx

app = FastAPI(title="LLM Gateway")
provider = MockProvider()

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]

@app.get("/health")
async def health():
    return {"status": "ok"}



@app.post("/v1/chat")
async def chat(req: ChatRequest):
    try:
        result = await provider.chat(req.model, req.messages)

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={"provider_status": e.response.status_code, "provider_body": e.response.text},
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Provider error: {e.response.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Provider timeout")
    return result





