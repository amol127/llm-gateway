import time
from collections import defaultdict, deque
from contextlib import contextmanager
from app.config import settings

samples: dict[str, deque] = defaultdict(lambda: deque(maxlen=5000))


@contextmanager
def timed(name: str):
    if not settings.timing_enabled:
        yield  # off by default: almost no cost
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        samples[name].append((time.perf_counter() - start) * 1000)


def summary() -> dict:
    out = {}
    for name, dq in samples.items():
        xs = sorted(dq)
        if not xs:
            continue
        out[name] = {
            "n": len(xs),
            "p50_ms": round(xs[len(xs) // 2], 1),
            "p95_ms": round(xs[min(len(xs) - 1, int(len(xs) * 0.95))], 1),
        }
    return out







