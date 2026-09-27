"""
Agent 7 — Script Guard (problem P13). Wraps security/script_safety.py with
governance: a BLOCK verdict can only be overridden by a senior role, and
every verdict and override is written to the tamper-evident audit log.
"""

from firstline.security.script_safety import assess
from firstline.governance.policy import can_override_script_block


def review_script(script: str, case_id: str, audit, requested_by_role: str = "l1_engineer") -> dict:
    result = assess(script)
    result["can_share_now"] = result["verdict"] == "ALLOW"
    result["override_allowed_for_requester"] = result["verdict"] == "BLOCK" and can_override_script_block(requested_by_role)
    audit.record(case_id, "script_guard", "script_assessed",
                 {"verdict": result["verdict"], "findings": [f["issue"] for f in result["findings"]]})
    return result
