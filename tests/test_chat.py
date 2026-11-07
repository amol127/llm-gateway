from fastapi.testclient import TestClient
import app.main as main
from app.main import app
from app.providers.mock import MockProvider
from app.reliability import Router

def test_chat(monkeypatch):
    monkeypatch.setattr(main, "router", Router([MockProvider(latency=0)]))
    client = TestClient(app)
    r = client.post("/v1/chat", json={"model": "x", "messages": [{"role": "user", "content": "hey"}]})
    assert r.status_code == 200
    assert r.json()["text"] == "mock reply to: hey"