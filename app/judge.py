import json
import re

from app.providers.base import Provider

JUDGE_PROMPT = """You are a strict grader. Compare the candidate answer to the reference answer.
Different wording is fine. Pass if the candidate states the same facts as the reference, even if it is shorter or reworded.
Mark "fail" if it contradicts the reference, adds claims the reference doesn't support, or misses the main point.

Question: {question}
Reference answer: {reference}
Candidate answer: {candidate}

Reply with ONLY JSON: {"verdict": "pass" or "fail", "reason": "one short sentence"}"""


def parse_verdict(text: str) -> tuple[str, str] | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        verdict = str(data["verdict"]).lower()
    except (json.JSONDecodeError, KeyError):
        return None
    if verdict not in ("pass", "fail"):
        return None
    return verdict, str(data.get("reason", ""))


async def judge(provider: Provider, model: str, question: str,
                reference: str, candidate: str) -> tuple[str, str] | None:
    prompt = (JUDGE_PROMPT
              .replace("{question}", question)
              .replace("{reference}", reference)
              .replace("{candidate}", candidate))
    for _ in range(2):  # one retry if the reply isn't valid JSON
        result = await provider.chat(model, [{"role": "user", "content": prompt}])
        parsed = parse_verdict(result.text)
        if parsed:
            return parsed
    return None  # counted as unparseable, never treated as a pass