from  fastapi import FastAPI 
from pydantic import BaseModel


app = FastAPI(title="LLM Gateway")


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/chat")
async def chat(req: ChatRequest):
    # Step 1: forward to a provider here
    return {"echo": req.messages[-1]["content"], "model": req.model}







