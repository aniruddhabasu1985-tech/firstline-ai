"""
Agent 5 — Commitment & Swarm Tracker (problems P5 missed meetings/messages,
P7 swarm timing and slow swarm follow-through).

Why (P5): under queue pressure, a promised 10am call or a customer's reply
gets missed. One missed meeting can undo weeks of goodwill.
Why (P7): engineers don't know WHEN to ask seniors for help — too early
wastes senior time, too late wastes the customer's. And when seniors do
reply, the answer sits unread because the engineer has several swarms open.

How:
  - Extracts commitments (meetings, "I'll update you by...") from the thread
    and creates internal reminders — the ONE place any agent has autonomy
    L3, because an internal reminder is low-risk, reversible and logged.
  - Flags customer messages unanswered past SLA.
  - Swarm decision: a transparent scoring rule (case age, attempts, no
    knowledge hit, severity, sentiment) instead of gut feel.
  - Swarm inbox: tracks every open swarm per engineer; nudges seniors when a
    swarm is unanswered and nudges the engineer when a reply is unread.
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta

MEETING = re.compile(r"\b(mon|tues|wednes|thurs|fri)day\b[^.]*?\b(\d{1,2})(:\d{2})?\s*(am|pm)\b\s*(ET|EST|PT|PST|CET|GMT|IST|JST)?", re.I)
PROMISE = re.compile(r"\bI(?:'ll| will) (update|get back to|call|send)[^.]*\bby\b[^.]*", re.I)


def extract_commitments(thread_text: str) -> list[dict]:
    items = []
    for m in MEETING.finditer(thread_text):
        items.append({"type": "meeting", "text": m.group(0).strip(), "reminders": ["T-60min", "T-10min"]})
    for m in PROMISE.finditer(thread_text):
        items.append({"type": "promise", "text": m.group(0).strip(), "reminders": ["T-60min"]})
    return items


def unanswered_customer_messages(messages: list[dict], now: datetime, sla_hours: float) -> list[dict]:
    """messages: [{'from': 'customer'|'engineer', 'at': datetime}] sorted by time."""
    if messages and messages[-1]["from"] == "customer":
        age = (now - messages[-1]["at"]).total_seconds() / 3600
        if age > sla_hours:
            return [{"waiting_hours": round(age, 1), "sla_hours": sla_hours}]
    return []


def swarm_score(case_age_days: float, attempts: int, kb_hit: bool, severity: int, sentiment: float) -> dict:
    score = 0
    reasons = []
    if case_age_days >= 3:
        score += 2; reasons.append("case open 3+ days")
    if attempts >= 2 and not kb_hit:
        score += 2; reasons.append("2+ attempts with no knowledge match")
    if not kb_hit and severity <= 2:
        score += 2; reasons.append("high severity with no knowledge match")
    if sentiment <= -0.5:
        score += 2; reasons.append("customer frustration rising")
    if attempts >= 3:
        score += 1; reasons.append("3+ troubleshooting attempts")
    return {"swarm": score >= 2, "score": score, "reasons": reasons}


def swarm_inbox(swarms: list[dict], now: datetime, senior_sla_h: float = 2, read_sla_h: float = 1) -> list[dict]:
    nudges = []
    for s in swarms:
        if s.get("replied_at") is None and (now - s["opened_at"]) > timedelta(hours=senior_sla_h):
            nudges.append({"swarm": s["id"], "to": "swarm_duty_lead", "why": "unanswered past senior SLA"})
        if s.get("replied_at") and not s.get("read_by_engineer") and (now - s["replied_at"]) > timedelta(hours=read_sla_h):
            nudges.append({"swarm": s["id"], "to": s["engineer"], "why": "senior replied; reply not yet read"})
    return nudges
