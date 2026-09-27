"""
FirstLine demo — one realistic case through the copilot, end to end.
Run: python demo.py   (no API keys needed)
"""
import json
from firstline.orchestrator import run_copilot
from firstline.agents import case_governance, commitments
from firstline.agents.script_guard import review_script
from firstline.governance.audit import AuditLog
from firstline.llm import Gateway

audit, gw = AuditLog(), Gateway()
case = {
    "case_id": "DEMO-1042", "country": "DE", "severity": 3, "product": "client", "deployment": "on_prem",
    "subject": "Client kann keine Verbindung zum Server herstellen",
    "body": ("Hallo, die Verbindung zum Server bricht ab und wir bekommen einen Fehler. "
             "Wir haben den Fiddler-Trace und die Server-Logs angehängt. Is this a proxy problem? "
             "Can we meet Tuesday at 10:00 am CET to look at it together?"),
    "provided_artifacts": ["fiddler trace", "server logs"],
    "logs": [{"type": "har", "content": '{"entries":[{"request":{"url":"https://srv/api"},"response":{"status":407}}]}'}],
}
draft = ("I hope this email finds you well! Kindly do the needful and share the Fiddler trace and server logs "
         "so we can check. We will update you.")

s = run_copilot(case, draft=draft, chosen_status="Hold", audit=audit, gateway=gw)
p = s["panel"]

print("\n=== ROUTING ===");        print(p["routing"])
print("\n=== KNOWLEDGE ===");      [print(" ", r) for r in p["knowledge"]["results"]]
print("\n=== LOG ANALYSIS ===");   print(" ", p["logs"][0]["findings"][0])
print("\n=== PRE-SEND CHECKS ON ENGINEER DRAFT ===")
print("  Repeat asks:", p["repeat_asks"])
print("  Status:", p["status_check"])
for i in p["compose"]["issues"]:
    print("  Compose:", i)
print("\n=== COMMITMENTS ===");     print(" ", commitments.extract_commitments(case["body"]))
print("\n=== LIVE SESSION? ===");   print(" ", case_governance.recommend_live_session(4, 4, 2))
print("\n=== SCRIPT GUARD ===")
print(" ", review_script("Get-ChildItem C:\\ProgramData\\App\\Cache | Remove-Item -Force", case["case_id"], audit))
print("\n=== GOVERNANCE ===")
print("  Blocked actions:", s["blocked_actions"])
print("  Audit entries:", len(audit.entries), "| chain verified:", audit.verify())
print(f"  LLM cost for this pass: ${gw.total_cost():.5f}")
