import hashlib
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.db import SessionLocal
from app.models import ApiKey
from app.timing import timed

_auth_cache: dict[str, tuple[float, int]] = {}
AUTH_TTL = 30.0

bearer = HTTPBearer(auto_error=False)


def generate_key() -> str:
    return "gw_" + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def authenticate(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing API key")

    with timed("auth"):
        key_hash = hash_key(creds.credentials)

        # 1) in-memory cache first
        hit = _auth_cache.get(key_hash)
        if hit and time.monotonic() < hit[0]:
            return hit[1]

        # 2) cache miss: look it up in Postgres, then release the connection
        async with SessionLocal() as session:
            row = await session.scalar(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.revoked.is_(False),
                )
            )
        if row is None:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # 3) remember only successful lookups
        _auth_cache[key_hash] = (time.monotonic() + AUTH_TTL, row.tenant_id)
        return row.tenant_id

    