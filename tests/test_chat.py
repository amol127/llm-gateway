from fastapi.testclient import TestClient
import app.main as main
from app.auth import authenticate
from app.main import app
from app.providers.mock import MockProvider
from app.reliability import Router
from app.ratelimit import rate_limit

# def test_chat(monkeypatch):
#     monkeypatch.setattr(main, "router", Router([MockProvider(latency=0)]))
#     client = TestClient(app)
#     r = client.post("/v1/chat", json={"model": "x", "messages": [{"role": "user", "content": "hey"}]})
#     assert r.status_code == 200
#     assert r.json()["text"] == "mock reply to: hey"




def test_chat(monkeypatch):
    async def no_log(**kwargs):
        pass
    async def no_cache(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "router", Router([MockProvider(latency=0)]))
    monkeypatch.setattr(main, "record_request", no_log)
    monkeypatch.setattr(main, "get_cached", no_cache)
    monkeypatch.setattr(main, "set_cached", no_cache)
    app.dependency_overrides[rate_limit] = lambda: 1
    app.dependency_overrides[rate_limit] = lambda: 1
    client = TestClient(app)
    r = client.post("/v1/chat", json={"model": "x", "messages": [{"role": "user", "content": "hey"}]})
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["text"] == "mock reply to: hey"

def test_chat_requires_key():
    client = TestClient(app)
    r = client.post("/v1/chat", json={"model": "x", "messages": []})
    assert r.status_code == 401



