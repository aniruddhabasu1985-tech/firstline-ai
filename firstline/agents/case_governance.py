"""
Agent 4 — Case Governance (problems P3 repeat asks, P4 wrong case status,
P12 forgotten accepted-defect cases, plus email ping-pong -> live session).

Why:
  P3  Asking a customer for a log they already sent is the fastest way to
      tell them nobody read their message. It also resets their clock.
  P4  Status drives automation. "Pending Customer" when the work is actually
      internal fires a chaser email at a customer who is waiting on us.
      "Hold" set without a customer request parks a case out of every SLA view.
  P12 Accepted-defect cases can wait months for an engineering fix. When the
      fix ships, nobody remembers to go back and tell the customer.
  Ping-pong: long email back-and-forth burns customer effort; past a point a
      20-minute live session is cheaper for everyone.

How: deterministic checks against the case record (free, explainable),
run BEFORE the engineer's reply goes out. Semantic repeat-detection uses a
mid-tier model only when keyword matching is inconclusive. Every output is
a suggestion (autonomy L1): the engineer stays accountable for the action.
"""

from __future__ import annotations
import re

ARTIFACTS = {
    "fiddler trace": [r"fiddler", r"\bhar\b", r"network trace"],
    "server logs": [r"server logs?", r"service logs?"],
    "connector log": [r"connector logs?", r"driver logs?"],
    "product version": [r"\bversion\b"],
    "screenshot": [r"screenshot", r"screen ?shot"],
    "powershell output": [r"powershell output", r"powershell"],
    "workflow file": [r"\bworkflow\b"],
    "event logs": [r"event logs?", r"event viewer"],
}
ASK_VERBS = re.compile(r"\b(share|send|attach|provide|upload|confirm|run .* again)\b", re.I)
INTERNAL = re.compile(r"\b(internal(ly)?|engineering team|our team|with (the )?(core|engineering|product) team|review(ing)? .* internally)\b", re.I)
CUSTOMER_ACTION = re.compile(r"(\?|\b(please|could you|can you|let us know|try the workaround)\b)", re.I)
CUSTOMER_HOLD = re.compile(r"\b(on hold|vacation|out of office|pause|get back (to you )?next week)\b", re.I)


def repeat_asks(already_provided: list[str], draft: str) -> list[str]:
    """Artifacts the draft asks for that the customer already provided."""
    if not ASK_VERBS.search(draft) and "?" not in draft:
        return []
    repeated = []
    for artifact in already_provided:
        for pattern in ARTIFACTS.get(artifact, [re.escape(artifact)]):
            if re.search(pattern, draft, re.I):
                repeated.append(artifact)
                break
    return repeated


def expected_status(draft: str, customer_requested_hold: bool, jira_linked: bool, says_defect: bool = False) -> str:
    if says_defect or re.search(r"\bproduct defect\b", draft, re.I):
        return "Accepted Defect" if jira_linked else "Pending Internal"
    if customer_requested_hold and CUSTOMER_HOLD.search(draft):
        return "Hold"
    if INTERNAL.search(draft):
        return "Pending Internal"
    if CUSTOMER_ACTION.search(draft):
        return "Pending Customer"
    return "Pending Internal"


def check_status(draft: str, chosen: str, customer_requested_hold: bool, jira_linked: bool) -> dict:
    exp = expected_status(draft, customer_requested_hold, jira_linked)
    reason = None
    if chosen != exp:
        if chosen == "Pending Customer" and exp == "Pending Internal":
            reason = "Reply says the work is on our side; 'Pending Customer' would send the customer a chaser email."
        elif chosen == "Hold":
            reason = "Hold should only be used when the customer asked to pause; otherwise the case leaves SLA views."
        elif chosen == "Accepted Defect":
            reason = "Accepted Defect requires a linked engineering ticket."
        else:
            reason = f"Reply content suggests '{exp}'."
    return {"chosen": chosen, "expected": exp, "ok": chosen == exp, "reason": reason}


def defect_watch(cases: list[dict], jira_status: dict[str, str]) -> list[dict]:
    """Accepted-defect cases whose linked defect has been fixed -> alert owner."""
    alerts = []
    for c in cases:
        if c.get("status") == "Accepted Defect" and jira_status.get(c.get("jira")) in {"fixed", "released"}:
            alerts.append({"case_id": c["case_id"], "owner": c["owner"], "jira": c["jira"],
                           "action": "Defect fixed — draft customer update with upgrade guidance and confirm resolution."})
    return alerts


def recommend_live_session(customer_emails: int, engineer_emails: int, clarification_loops: int) -> dict:
    exchanges = min(customer_emails, engineer_emails)
    recommend = exchanges >= 4 or clarification_loops >= 2
    return {"recommend": recommend,
            "reason": (f"{exchanges} email exchanges / {clarification_loops} clarification loops — "
                       "offer a live troubleshooting session to cut customer effort.") if recommend else None}
