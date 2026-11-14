import argparse
import asyncio
import json
from pathlib import Path

import httpx

from app.judge import judge
from app.providers.gemini import GeminiProvider

PAUSE_SECONDS = 7  # keeps you under a ~10 requests/minute free-tier limit


async def judge_with_retry(provider, model, row, max_attempts: int = 6):
    for attempt in range(max_attempts):
        try:
            return await judge(provider, model, row["question"], row["reference"], row["candidate"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429:
                raise  # a real error: don't hide it
            retry_after = e.response.headers.get("retry-after")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else 5 * 2 ** attempt
            print(f"  rate limited, waiting {wait:.0f}s (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(wait)
    return "rate_limited"


async def main(model: str, path: str) -> None:
    provider = GeminiProvider()
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]

    agree = false_pass = false_fail = unparsed = skipped = 0
    disagreements = []
    for i, r in enumerate(rows, 1):
        out = await judge_with_retry(provider, model, r)
        
        verdict, reason = out if isinstance(out, tuple) else (out, "")
        print(f"[{i}/{len(rows)}] human={r['human']} judge={verdict}  {reason}")
        # verdict = await judge_with_retry(provider, model, r)
        # print(f"[{i}/{len(rows)}] human={r['human']} judge={verdict}")
        if verdict == "rate_limited":
            skipped += 1
        elif verdict is None:
            unparsed += 1
        elif verdict == r["human"]:
            agree += 1
        else:
            disagreements.append(r)
            if verdict == "pass":
                false_pass += 1  # judge approved a bad answer: the dangerous error
            else:
                false_fail += 1
        await asyncio.sleep(PAUSE_SECONDS)

    scored = len(rows) - skipped
    print(f"\nexamples scored: {scored} of {len(rows)}  (skipped by rate limit: {skipped})")
    if scored:
        print(f"agreement:       {agree / scored:.1%}")
    print(f"false passes:    {false_pass}  (judge approved a human-failed answer)")
    print(f"false fails:     {false_fail}")
    print(f"unparseable:     {unparsed}")
    for d in disagreements:
        print(f"\nDISAGREEMENT (human said {d['human']}):")
        print(f"  Q: {d['question']}\n  ref: {d['reference']}\n  cand: {d['candidate']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--data", default="evals/labeled.jsonl")
    args = p.parse_args()
    asyncio.run(main(args.model, args.data))