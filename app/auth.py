# import hashlib
# import secrets
# from fastapi import Depends, Header, HTTPException
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.db import get_session
# from app.models import ApiKey

# def generate_key() -> str:
#     return "gw_" + secrets.token_urlsafe(32)

# def hash_key(key: str) -> str:
#     return hashlib.sha256(key.encode()).hexdigest()

# async def authenticate(
#     authorization: str | None = Header(default=None),
#     session: AsyncSession = Depends(get_session),
# ) -> int:
#     """Returns the tenant_id for a valid key, else 401."""
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="Missing API key")
#     key = authorization.removeprefix("Bearer ").strip()
#     row = await session.scalar(
#         select(ApiKey).where(ApiKey.key_hash == hash_key(key), ApiKey.revoked.is_(False))
#     )
#     if row is None:
#         raise HTTPException(status_code=401, detail="Invalid API key")
#     return row.tenant_id




import hashlib
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.models import ApiKey

bearer = HTTPBearer(auto_error=False)

def generate_key() -> str:
    return "gw_" + secrets.token_urlsafe(32)

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

async def authenticate(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> int:
    """Returns the tenant_id for a valid key, else 401."""
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    row = await session.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == hash_key(creds.credentials),
            ApiKey.revoked.is_(False),
        )
    )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return row.tenant_id



