"""
Governance policy engine — decides what each agent is ALLOWED to do.

Why: the single most important design decision in this project is that the
AI assists engineers; it does not act on customers. Every agent has an
explicit autonomy level, and every action is checked against an allowlist
here — in plain, reviewable code — rather than being left to model judgment.

Autonomy levels (adapted from standard human-in-the-loop AI governance):
  L0 OBSERVE  - agent may read and analyze only
  L1 SUGGEST  - agent may show suggestions to the engineer
  L2 DRAFT    - agent may prepare a draft the engineer must approve
  L3 ACT_LOW  - agent may take a low-risk internal action automatically
                (e.g. set an internal reminder), fully logged and reversible
  L4 ACT      - agent acts on customer-visible state. NOT GRANTED TO ANY AGENT.

Nothing customer-facing is ever sent without a human click. Case status
changes are suggested, never applied. Script verdicts of BLOCK require a
named senior approver to override.
"""

from __future__ import annotations
from enum import IntEnum


class Autonomy(IntEnum):
    OBSERVE = 0
    SUGGEST = 1
    DRAFT = 2
    ACT_LOW = 3
    ACT = 4


AGENT_AUTONOMY = {
    "smart_routing": Autonomy.SUGGEST,       # recommends queue/engineer; routing rules apply it after pilot sign-off
    "unified_knowledge": Autonomy.SUGGEST,
    "knowledge_capture": Autonomy.DRAFT,      # drafts KB articles for knowledge workers to approve
    "compose_assist": Autonomy.DRAFT,
    "case_governance": Autonomy.SUGGEST,
    "commitment_tracker": Autonomy.ACT_LOW,   # may create internal reminders only
    "log_analysis": Autonomy.SUGGEST,
    "script_guard": Autonomy.SUGGEST,
}

ACTION_REQUIREMENTS = {
    "show_suggestion": Autonomy.SUGGEST,
    "prepare_draft": Autonomy.DRAFT,
    "create_internal_reminder": Autonomy.ACT_LOW,
    "send_customer_reply": Autonomy.ACT,
    "change_case_status": Autonomy.ACT,
    "close_case": Autonomy.ACT,
    "share_script_with_customer": Autonomy.ACT,
}

SENIOR_APPROVER_ROLES = {"core_engineer", "support_lead", "support_manager"}


def is_allowed(agent: str, action: str) -> bool:
    return AGENT_AUTONOMY.get(agent, Autonomy.OBSERVE) >= ACTION_REQUIREMENTS[action]


def can_override_script_block(role: str) -> bool:
    return role in SENIOR_APPROVER_ROLES
