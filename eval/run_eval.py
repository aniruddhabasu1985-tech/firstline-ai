"""
Component-level evaluation against synthetic ground truth.

Measures each agent on the exact failure it exists to prevent. These are
accuracy numbers for the AGENTS, measured here. The KPI impact numbers in
the ROI model are PROJECTIONS with stated assumptions — the two are kept
separate on purpose (see docs/09-roi.md), and a pilot is required to
replace projections with measured results.

Usage: python -m eval.run_eval
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from firstline.agents import routing, compose, case_governance, log_analysis, commitments
from firstline.agents.knowledge import UnifiedKnowledge
from firstline.security.injection import screen
from firstline.security.pii import redact
from firstline.security.script_safety import assess
from firstline.governance.audit import AuditLog
from firstline.orchestrator import run_copilot
from firstline.llm import Gateway

SETS = Path(__file__).resolve().parents[1] / "data" / "eval_sets"
OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)


def load(n):
    return json.loads((SETS / f"{n}.json").read_text())


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def run() -> dict:
    r = {}
    rt = load("routing")
    ok = sum(routing.route(s, t, c, sev, p)["queue"] == exp for s, c, t, sev, p, _prod, exp in rt)
    r["smart_routing_accuracy"] = pct(ok, len(rt))

    kb = UnifiedKnowledge()
    kq = load("knowledge_queries")
    hit1 = sum(1 for q, dep, exp in kq if kb.search(q, dep, 1) and kb.search(q, dep, 1)[0]["id"] == exp)
    hit3 = sum(1 for q, dep, exp in kq if exp in [h["id"] for h in kb.search(q, dep, 3)])
    r["knowledge_hit_at_1"] = pct(hit1, len(kq))
    r["knowledge_hit_at_3"] = pct(hit3, len(kq))
    defects = [(q, dep, exp) for q, dep, exp in kq if exp.startswith("JIRA")]
    r["known_defect_detection"] = pct(sum(1 for q, dep, exp in defects if (kb.known_defect(q, dep) or {}).get("id") == exp), len(defects))
    novel_checks = [("Resolved by setting TNS_ADMIN for the service account", False),
                    ("Resolved by disabling GPU acceleration in the rendering settings of the map tool", True)]
    r["novelty_detection_accuracy"] = pct(sum(kb.is_novel(t) == exp for t, exp in novel_checks), len(novel_checks))

    ra = load("repeat_asks")
    tp = fp = fn = 0
    for provided, draft, exp in ra:
        got = bool(case_governance.repeat_asks(provided, draft))
        tp += got and exp; fp += got and not exp; fn += (not got) and exp
    r["repeat_ask_precision"] = pct(tp, tp + fp)
    r["repeat_ask_recall"] = pct(tp, tp + fn)

    st = load("statuses")
    r["status_validation_accuracy"] = pct(sum(case_governance.check_status(d, ch, hold, jira)["expected"] == exp
                                              for d, hold, jira, ch, exp in st), len(st))
    wrong = [(d, hold, jira, ch, exp) for d, hold, jira, ch, exp in st if ch != exp]
    r["wrong_status_caught"] = pct(sum(not case_governance.check_status(d, ch, hold, jira)["ok"]
                                       for d, hold, jira, ch, exp in wrong), len(wrong))

    lg = load("logs")
    r["log_signature_accuracy"] = pct(sum(log_analysis.analyze(t, c)["top_signature"] == exp for t, c, exp in lg), len(lg))

    sc = load("scripts")
    r["script_verdict_accuracy"] = pct(sum(assess(s)["verdict"] == exp for s, exp in sc), len(sc))
    dangerous = [s for s, exp in sc if exp == "BLOCK"]
    r["destructive_scripts_blocked"] = pct(sum(assess(s)["verdict"] == "BLOCK" for s in dangerous), len(dangerous))

    cp = load("compose")
    r["compose_issue_detection"] = pct(sum(compose.review_draft(d)["issue_types"] == exp for d, exp in cp), len(cp))

    sw = load("swarm")
    r["swarm_decision_accuracy"] = pct(sum(commitments.swarm_score(a, t, k, sev, sen)["swarm"] == exp
                                           for a, t, k, sev, sen, exp in sw), len(sw))

    inj = load("injection")
    r["injection_detection_accuracy"] = pct(sum(screen(t)[0] == exp for t, exp in inj), len(inj))
    pii = load("pii")
    r["pii_redaction_recall"] = pct(sum(min(redact(t)[1], exp) for t, exp in pii), sum(exp for _, exp in pii))

    # End-to-end copilot pass + cost per case
    gw, audit = Gateway(), AuditLog()
    demo_case = {"case_id": "EVAL-1", "subject": "Proxy 407 error when connecting client to server",
                 "body": "Hi, we attached the Fiddler trace. Why does the client fail? Can you advise?",
                 "country": "US", "severity": 3, "product": "client", "deployment": "any",
                 "provided_artifacts": ["fiddler trace"],
                 "logs": [{"type": "har", "content": '{"entries":[{"response":{"status":407}}]}'}]}
    run_copilot(demo_case, draft="Kindly share the Fiddler trace so we can check.", chosen_status="Pending Customer",
                audit=audit, gateway=gw)
    r["llm_cost_per_case_usd"] = round(gw.total_cost(), 5)
    r["audit_chain_verified"] = audit.verify()

    out = {"run_at": datetime.now().isoformat(timespec="seconds"), "metrics": r}
    (OUT / "latest_eval.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    res = run()
    for k, v in res["metrics"].items():
        print(f"{k:38s} {v}")


def run_heldout() -> dict:
    """Scores the same agents on the held-out set (not used for tuning)."""
    h = lambda n: json.loads((SETS / f"heldout_{n}.json").read_text())
    kb = UnifiedKnowledge()
    r = {}
    rt = h("routing")
    r["smart_routing_accuracy"] = pct(sum(routing.route(s, t, c, sev, p)["queue"] == exp for s, c, t, sev, p, _x, exp in rt), len(rt))
    kq = h("knowledge_queries")
    r["knowledge_hit_at_3"] = pct(sum(exp in [x["id"] for x in kb.search(q, dep, 3)] for q, dep, exp in kq), len(kq))
    ra = h("repeat_asks")
    r["repeat_ask_accuracy"] = pct(sum(bool(case_governance.repeat_asks(p, d)) == e for p, d, e in ra), len(ra))
    st = h("statuses")
    r["status_validation_accuracy"] = pct(sum(case_governance.check_status(d, ch, ho, j)["expected"] == e for d, ho, j, ch, e in st), len(st))
    lg = h("logs")
    r["log_signature_accuracy"] = pct(sum(log_analysis.analyze(t, c)["top_signature"] == e for t, c, e in lg), len(lg))
    sc = h("scripts")
    r["script_verdict_accuracy"] = pct(sum(assess(s)["verdict"] == e for s, e in sc), len(sc))
    cp = h("compose")
    r["compose_issue_detection"] = pct(sum(compose.review_draft(d)["issue_types"] == e for d, e in cp), len(cp))
    return r


if __name__ == "__main__":
    print("\n--- HELD-OUT (not used for tuning) ---")
    ho = run_heldout()
    for k, v in ho.items():
        print(f"{k:38s} {v}")
    data = json.loads((OUT / "latest_eval.json").read_text())
    data["heldout_metrics"] = ho
    (OUT / "latest_eval.json").write_text(json.dumps(data, indent=2))
    v2 = json.loads((SETS / "heldout_v2_scripts.json").read_text())
    data["heldout_v2_script_guard_after_fail_closed_fix"] = pct(sum(assess(s)["verdict"] == e for s, e in v2), len(v2))
    data["heldout_v2_destructive_blocked"] = pct(sum(assess(s)["verdict"] == "BLOCK" for s, e in v2 if e == "BLOCK"),
                                                 sum(1 for _, e in v2 if e == "BLOCK"))
    data["heldout_v2_destructive_auto_allowed"] = sum(assess(s)["verdict"] == "ALLOW" for s, e in v2 if e == "BLOCK")
    (OUT / "latest_eval.json").write_text(json.dumps(data, indent=2))
    print("\n--- FRESH HELD-OUT v2 (script guard, after fail-closed redesign) ---")
    print("script_verdict_accuracy               ", data["heldout_v2_script_guard_after_fail_closed_fix"])
    print("destructive_scripts_blocked           ", data["heldout_v2_destructive_blocked"])
    print("destructive_scripts_AUTO_ALLOWED      ", data["heldout_v2_destructive_auto_allowed"], "(safety metric: must be 0)")
