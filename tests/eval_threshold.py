import asyncio
import numpy as np
from app.semantic import embed

SAME = [  # should hit the cache
    ("what is a circuit breaker", "explain circuit breakers"),
    ("how do I reset my password", "I forgot my password, how can I reset it"),
    ("what is a rate limiter", "explain rate limiting"),
    ("how to cancel my subscription", "how can I cancel my plan"),
]
DIFFERENT = [  # must NOT hit the cache
    ("how do I reset my password", "how do I change my email address"),
    ("what is a rate limiter", "what is a circuit breaker"),
    ("how to cancel my subscription", "how to upgrade my subscription"),
    ("what is python", "what is a python snake"),
]

def cos(a, b):
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

async def main():
    same = [cos(await embed(a), await embed(b)) for a, b in SAME]
    diff = [cos(await embed(a), await embed(b)) for a, b in DIFFERENT]
    print("same-meaning similarities:", [round(x, 3) for x in same])
    print("different-meaning similarities:", [round(x, 3) for x in diff])
    print(f"{'thr':>5} {'hit rate':>9} {'false hits':>11}")
    for t in np.arange(0.70, 0.99, 0.02):
        hit = sum(s >= t for s in same) / len(same)
        false = sum(s >= t for s in diff) / len(diff)
        print(f"{t:5.2f} {hit:9.0%} {false:11.0%}")

asyncio.run(main())