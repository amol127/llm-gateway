from fastapi.testclient import TestClient
import app.main as main
from app.auth import authenticate
from app.main import app
from app.providers.mock import MockProvider
from app.reliability import Router

# def test_chat(monkeypatch):
#     monkeypatch.setattr(main, "router", Router([MockProvider(latency=0)]))
#     client = TestClient(app)
#     r = client.post("/v1/chat", json={"model": "x", "messages": [{"role": "user", "content": "hey"}]})
#     assert r.status_code == 200
#     assert r.json()["text"] == "mock reply to: hey"




def test_chat(monkeypatch):
    monkeypatch.setattr(main, "router", Router([MockProvider(latency=0)]))
    app.dependency_overrides[authenticate] = lambda: 1
    client = TestClient(app)
    r = client.post("/v1/chat", json={"model": "x", "messages": [{"role": "user", "content": "hey"}]})
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["text"] == "mock reply to: hey"

def test_chat_requires_key():
    client = TestClient(app)
    r = client.post("/v1/chat", json={"model": "x", "messages": []})
    assert r.status_code == 401



