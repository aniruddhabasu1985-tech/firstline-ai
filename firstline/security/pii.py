"""
PII / secrets redaction — runs on every prompt before it reaches any model.

Why: B2B support threads routinely contain customer emails, phone numbers,
server hostnames, IPs, connection strings and, worst of all, credentials
pasted into logs. None of that is needed for the model to reason about the
problem, and all of it creates regulatory exposure (GDPR for EU customers,
contractual data-handling clauses for everyone) if sent to a third party.

How: deterministic pattern redaction with typed placeholders, so the model
still knows *that* an IP or email existed ("<IP_1>") without seeing the value.
In production this is paired with a managed DLP service; the pattern layer
stays as a defense-in-depth backstop that cannot be misconfigured remotely.
"""

import re

_PATTERNS = [
    ("SECRET", re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*\S+")),
    ("CONNSTR", re.compile(r"(?i)\b(server|data source)=[^;\s]+;[^\s]*")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("PHONE", re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]


def redact(text: str) -> tuple[str, int]:
    count = 0
    for label, pattern in _PATTERNS:
        seen: dict[str, str] = {}

        def _sub(m, label=label, seen=seen):
            nonlocal count
            count += 1
            key = m.group(0)
            if key not in seen:
                seen[key] = f"<{label}_{len(seen) + 1}>"
            return seen[key]

        text = pattern.sub(_sub, text)
    return text, count
