import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.providers.mock import MockProvider
from app.reliability import Router


def load_cases(path: str) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def check(case: dict, output: str) -> list[str]:
    out = output.lower()
    failures = []
    for s in case.get("must_contain", []):
        if s.lower() not in out:
            failures.append(f"missing: {s}")
    for s in case.get("must_not_contain", []):
        if s.lower() in out:
            failures.append(f"forbidden: {s}")
    return failures


async def run(prompt_path: str, cases_path: str) -> list[dict]:
    template = Path(prompt_path).read_text(encoding="utf-8")
    router = Router([MockProvider(latency=0)])  # swap in real providers later
    results = []
    for case in load_cases(cases_path):
        prompt = template.replace("{question}", case["input"])
        _, res = await router.chat("eval-model", [{"role": "user", "content": prompt}])
        failures = check(case, res.text)
        results.append({"id": case["id"], "passed": not failures, "failures": failures})
    return results


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", default="prompts/support.txt")
    p.add_argument("--cases", default="evals/cases.jsonl")
    p.add_argument("--baseline", default="evals/baseline.json")
    p.add_argument("--max-drop", type=float, default=0.05)
    p.add_argument("--update-baseline", action="store_true")
    args = p.parse_args()

    results = asyncio.run(run(args.prompt, args.cases))
    score = sum(r["passed"] for r in results) / len(results)

    for r in results:
        print(("PASS " if r["passed"] else "FAIL ") + r["id"], *r["failures"])
    print(f"\nscore: {score:.2%} ({sum(r['passed'] for r in results)}/{len(results)})")

    baseline_file = Path(args.baseline)
    if args.update_baseline or not baseline_file.exists():
        baseline_file.write_text(json.dumps({"score": score}, indent=2))
        print(f"baseline saved: {score:.2%}")
        return 0

    baseline = json.loads(baseline_file.read_text())["score"]
    print(f"baseline: {baseline:.2%}, allowed drop: {args.max_drop:.0%}")
    if score < baseline - args.max_drop:
        print("GATE FAILED: quality dropped below the baseline")
        return 1
    print("GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())