"""
Case copilot orchestration (LangGraph).

Runs at two moments in a case's life:
  - INTAKE: route the case, pre-fetch knowledge, analyze attached logs, so
    the engineer opens a case that already has a head start (drives FDR).
  - PRE-SEND: when the engineer drafts a reply, run compose + case-governance
    checks before anything reaches the customer (drives CSAT, stops misses).

Every node's output passes through `governance_gate`, which drops any
proposed action an agent is not authorized for and writes an audit entry.
The graph returns a "copilot panel" — suggestions for a human, never
actions on a customer.
"""

from __future__ import annotations
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from firstline.agents import routing, compose, case_governance, log_analysis
from firstline.agents.knowledge import UnifiedKnowledge
from firstline.governance.audit import AuditLog
from firstline.governance.policy import is_allowed
from firstline.security.injection import screen
from firstline.llm import Gateway

_KB = UnifiedKnowledge()


class CaseState(TypedDict, total=False):
    case: dict
    draft: Optional[str]
    chosen_status: Optional[str]
    panel: dict
    blocked_actions: list
    audit: AuditLog
    gateway: Gateway


def n_security(s: CaseState) -> CaseState:
    flagged, hits = screen(s["case"]["body"])
    s["panel"]["security"] = {"injection_suspected": flagged, "signals": hits}
    if flagged:
        s["audit"].record(s["case"]["case_id"], "security", "injection_suspected", {"signals": len(hits)})
    return s


def n_route(s: CaseState) -> CaseState:
    c = s["case"]
    s["panel"]["routing"] = routing.route(c["subject"], c["body"], c["country"], c["severity"], c.get("premium", False))
    s["gateway"].call("classify_case", c["subject"] + c["body"], offline_result=s["panel"]["routing"]["queue"], est_out_tokens=40)
    return s


def n_knowledge(s: CaseState) -> CaseState:
    c = s["case"]
    q = c["subject"] + " " + c["body"]
    s["panel"]["knowledge"] = {"results": _KB.search(q, c.get("deployment", "any")),
                               "known_defect": _KB.known_defect(q, c.get("deployment", "any"))}
    s["gateway"].call("rag_answer", q, offline_result="grounded summary", est_out_tokens=250)
    return s


def n_logs(s: CaseState) -> CaseState:
    s["panel"]["logs"] = [log_analysis.analyze(l["type"], l["content"]) for l in s["case"].get("logs", [])]
    for r in s["panel"]["logs"]:
        if r["needs_model_review"]:
            s["gateway"].call("log_long_context", "unmatched log lines", offline_result="summary", est_out_tokens=300)
    return s


def n_pre_send(s: CaseState) -> CaseState:
    draft = s.get("draft")
    if not draft:
        return s
    c = s["case"]
    s["panel"]["compose"] = compose.review_draft(draft, c["body"], c.get("product"))
    s["panel"]["repeat_asks"] = case_governance.repeat_asks(c.get("provided_artifacts", []), draft)
    if s.get("chosen_status"):
        s["panel"]["status_check"] = case_governance.check_status(
            draft, s["chosen_status"], c.get("customer_requested_hold", False), bool(c.get("jira")))
    s["gateway"].call("compose_reply", draft, offline_result="rewrite", est_out_tokens=300)
    return s


def governance_gate(s: CaseState) -> CaseState:
    proposed = [("compose_assist", "prepare_draft"), ("case_governance", "show_suggestion"),
                ("compose_assist", "send_customer_reply"), ("case_governance", "change_case_status")]
    allowed, blocked = [], []
    for agent, action in proposed:
        (allowed if is_allowed(agent, action) else blocked).append(f"{agent}:{action}")
    s["blocked_actions"] = blocked
    s["audit"].record(s["case"]["case_id"], "governance_gate", "panel_released",
                      {"allowed": allowed, "blocked": blocked, "sections": sorted(s["panel"].keys())})
    return s


def build():
    g = StateGraph(CaseState)
    for name, fn in [("security", n_security), ("route", n_route), ("knowledge", n_knowledge),
                     ("logs", n_logs), ("pre_send", n_pre_send), ("gate", governance_gate)]:
        g.add_node(name, fn)
    g.set_entry_point("security")
    for a, b in [("security", "route"), ("route", "knowledge"), ("knowledge", "logs"), ("logs", "pre_send"), ("pre_send", "gate")]:
        g.add_edge(a, b)
    g.add_edge("gate", END)
    return g.compile()


_APP = build()


def run_copilot(case: dict, draft: str | None = None, chosen_status: str | None = None,
                audit: AuditLog | None = None, gateway: Gateway | None = None) -> CaseState:
    return _APP.invoke({"case": case, "draft": draft, "chosen_status": chosen_status, "panel": {},
                        "blocked_actions": [], "audit": audit or AuditLog(), "gateway": gateway or Gateway()})
