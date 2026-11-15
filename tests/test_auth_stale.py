import asyncio
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import OperationalError

import app.auth as auth


class BrokenSession:
    def __call__(self):
        return self

    async def __aenter__(self):
        raise OperationalError("select 1", {}, Exception("db down"))

    async def __aexit__(self, *a):
        return False


def _creds(key="k"):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=key)


def test_serves_stale_key_when_db_down(monkeypatch):
    monkeypatch.setattr(auth, "SessionLocal", BrokenSession())
    monkeypatch.setattr(auth, "_auth_cache", {auth.hash_key("k"): (time.monotonic() - 10, 7)})
    assert asyncio.run(auth.authenticate(_creds())) == 7


def test_unknown_key_gets_503_when_db_down(monkeypatch):
    monkeypatch.setattr(auth, "SessionLocal", BrokenSession())
    monkeypatch.setattr(auth, "_auth_cache", {})
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.authenticate(_creds("never-seen")))
    assert e.value.status_code == 503



def test_breaker_stops_hammering_dead_db(monkeypatch):
    calls = {"n": 0}

    class Counting(BrokenSession):
        async def __aenter__(self):
            calls["n"] += 1
            return await super().__aenter__()

    monkeypatch.setattr(auth, "SessionLocal", Counting())
    monkeypatch.setattr(auth, "db_breaker", auth.CircuitBreaker(failure_threshold=2, cooldown=60))
    monkeypatch.setattr(auth, "_auth_cache", {auth.hash_key("k"): (time.monotonic() - 10, 7)})

    for _ in range(10):
        assert asyncio.run(auth.authenticate(_creds())) == 7

    assert calls["n"] == 2  # two real attempts, then the breaker kept the other 8 away