from fastapi.testclient import TestClient
from app.main import app
import app.main as main
from app.providers.base import ChatResult

class FakeProvider:
    async def chat(self, model, messages):
        return ChatResult(text="hi", model=model, input_tokens=1, output_tokens=1)

def test_chat(monkeypatch):
    monkeypatch.setattr(main, "provider", FakeProvider())
    client = TestClient(app)
    r = client.post("/v1/chat", json={"model": "x", "messages": [{"role": "user", "content": "hey"}]})
    assert r.status_code == 200
    assert r.json()["text"] == "hi"