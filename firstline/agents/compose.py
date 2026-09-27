"""
Agent 3 — Compose Assist (problems P1 language/comprehension, P6 generic
pasted AI answers, P10 no value-added support).

Why: engineers who are strong troubleshooters but not native English writers
lose customers in the writing, not the fixing — misread asks, phrasing that
reads as rude or vague to native speakers, and (the newest failure mode)
generic chatbot text pasted in without reference to the customer's actual
environment. Each of these costs CSAT and adds another email round trip.

How, two directions:
  - INBOUND ("what is the customer really asking?"): extracts every explicit
    question/ask from the customer message, and can explain the message in
    the engineer's native language so the ask is understood before replying.
  - OUTBOUND ("will my reply land well?"): checks the draft for (a) phrasing
    that native speakers commonly misread, (b) generic AI boilerplate with no
    case-specific content, (c) customer questions left unanswered, then
    offers a rewrite plus one relevant best-practice / feature tip (P10).
The engineer always sends; the agent only drafts (autonomy L2).
"""

from __future__ import annotations
import re

NON_NATIVE = {
    r"\bdo the needful\b": "State the exact action you need, e.g. 'Could you please share the server logs?'",
    r"\brevert back\b": "Use 'reply' or 'get back to us'.",
    r"\bPFA\b": "Use 'I've attached ...'.",
    r"\bthe same is\b": "Name the thing directly, e.g. 'the connector is ...'.",
    r"\bkindly\b": "Use 'please' — 'kindly' can read as demanding to native speakers.",
    r"\bprepone\b": "Use 'bring forward' or 'move earlier'.",
    r"\bwe will update you\b": "Give a specific time: 'I'll update you by 3pm ET tomorrow.'",
    r"\bas per your (email|mail)\b": "Use 'as you mentioned'.",
}
GENERIC_AI = [
    r"i hope this (email|message) finds you well",
    r"^certainly!", r"\bcertainly! here (are|is)\b", r"as an ai\b", r"\bdelve\b",
    r"in today's fast-paced", r"general troubleshooting steps", r"restart your computer",
    r"check your internet connection",
]
SPECIFICITY = re.compile(r"\b(\d{3,4}|error|trace|log|version|connector|server|workflow|proxy|certificate|schedule|odbc|saml)\b", re.I)
QUESTION = re.compile(r"[^.?!]*\?")

BEST_PRACTICE = {
    "server": "Tip: enabling the built-in health-check schedule catches worker failures before users notice.",
    "connectors": "Tip: filtering at source in the connector query usually cuts extract time and timeout risk.",
    "client": "Tip: keeping the temp directory on a local SSD noticeably speeds up large workflows.",
}


def extract_asks(customer_message: str) -> list[str]:
    return [q.strip() for q in QUESTION.findall(customer_message) if len(q.strip()) > 5]


def review_draft(draft: str, customer_message: str = "", product: str | None = None) -> dict:
    issues = []
    lower = draft.lower()
    for pattern, fix in NON_NATIVE.items():
        if re.search(pattern, draft, re.I):
            issues.append({"type": "non_native_phrasing", "match": pattern.strip("\\b"), "suggestion": fix})
    generic_hits = [p for p in GENERIC_AI if re.search(p, lower, re.M)]
    if generic_hits or (len(draft) > 120 and not SPECIFICITY.search(draft)):
        issues.append({"type": "generic_ai_text",
                       "suggestion": "Reply references nothing specific to this customer's environment. "
                                     "Cite what you found in their logs/trace and the exact next step."})
    unanswered = []
    for ask in extract_asks(customer_message):
        key_terms = [w for w in re.findall(r"[a-z]{5,}", ask.lower())][:3]
        if key_terms and not any(t in lower for t in key_terms):
            unanswered.append(ask)
    if unanswered:
        issues.append({"type": "unanswered_customer_question", "questions": unanswered})
    return {"issues": issues, "issue_types": sorted({i["type"] for i in issues}),
            "value_add_tip": BEST_PRACTICE.get(product or "", None)}
