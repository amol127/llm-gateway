import logging
from app.db import SessionLocal
from app.models import RequestLog

log = logging.getLogger("gateway.tracing")

async def record_request(**fields) -> None:
    """Never raises: a logging failure must not break a user's request."""
    try:
        async with SessionLocal() as session:
            session.add(RequestLog(**fields))
            await session.commit()
    except Exception:
        log.exception("failed to write request log")