import logging
import asyncio
from app.db import SessionLocal
from app.models import RequestLog
from app.timing import timed


log = logging.getLogger("gateway.tracing")
_queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)


async def record_request(**fields) -> None:
    """Never raises: a logging failure must not break a user's request."""
    try:
        with timed("log_insert"):

            async with SessionLocal() as session:
                session.add(RequestLog(**fields))
                await session.commit()
    except Exception:
        log.exception("failed to write request log")



def enqueue_request(**fields) -> None:
    """Called from request handlers. Never blocks and never raises."""
    try:
        _queue.put_nowait(fields)
    except asyncio.QueueFull:
        log.warning("log queue full, dropping a row")


async def log_writer() -> None:
    while True:
        batch = [await _queue.get()]
        await asyncio.sleep(0.1)  # let more rows pile up
        while not _queue.empty() and len(batch) < 500:
            batch.append(_queue.get_nowait())
        try:
            with timed("log_insert_batch"):
                async with SessionLocal() as s:
                    s.add_all([RequestLog(**f) for f in batch])
                    await s.commit()
        except Exception:
            log.exception("failed to write %d request logs", len(batch))





