import time
from collections import defaultdict
from contextlib import contextmanager

samples: dict[str, list[float]] = defaultdict(list)


@contextmanager
def timed(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        samples[name].append((time.perf_counter() - start) * 1000)


def summary() -> dict:
    out = {}
    for name, xs in samples.items():
        xs = sorted(xs)
        out[name] = {
            "n": len(xs),
            "p50_ms": round(xs[len(xs) // 2], 1),
            "p95_ms": round(xs[int(len(xs) * 0.95)], 1),
        }
    return out