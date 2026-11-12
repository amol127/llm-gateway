import re

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("api_key", re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{20,}|gw_[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,})\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("card", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")),
    ("aadhaar", re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)")),
    ("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
]


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def mask_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for kind, pattern in PATTERNS:
        def repl(m: re.Match, kind: str = kind) -> str:
            if kind == "card":
                digits = re.sub(r"\D", "", m.group())
                if not (13 <= len(digits) <= 19 and luhn_ok(digits)):
                    return m.group()  # long number that isn't a real card
            counts[kind] = counts.get(kind, 0) + 1
            return f"[{kind.upper()}]"
        text = pattern.sub(repl, text)
    return text, counts


def apply_guardrails(messages: list[dict]) -> tuple[list[dict], dict[str, int]]:
    total: dict[str, int] = {}
    out = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            masked, counts = mask_text(content)
            for k, v in counts.items():
                total[k] = total.get(k, 0) + v
            out.append({**m, "content": masked})
        else:
            out.append(m)
    return out, total