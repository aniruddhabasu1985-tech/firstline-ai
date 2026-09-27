from datetime import datetime, timedelta
from firstline.agents import routing, compose, case_governance, commitments, log_analysis
from firstline.agents.knowledge import UnifiedKnowledge
from firstline.orchestrator import run_copilot


def test_routing_by_language_and_region():
    assert routing.route("x", "Die Verbindung bricht ab, bitte helfen Sie uns", "DE", 3, False)["queue"] == "L1-EMEA-DE"
    assert routing.route("x", "down", "US", 1, False)["queue"] == "CORE-SEV1"


def test_knowledge_surfaces_known_defect():
    kb = UnifiedKnowledge()
    d = kb.known_defect("rows missing unicode column names warehouse", "cloud")
    assert d and d["id"] == "JIRA-4411"


def test_novel_resolution_triggers_kb_draft():
    kb = UnifiedKnowledge()
    assert kb.is_novel("Disabled GPU acceleration in rendering settings of the map tool")
    draft = kb.draft_kb_article("C9", "Map tool crashes", "Disable GPU acceleration")
    assert draft["status"] == "DRAFT_PENDING_KNOWLEDGE_WORKER_REVIEW"


def test_compose_flags_generic_and_non_native():
    r = compose.review_draft("Kindly do the needful and revert back.")
    assert "non_native_phrasing" in r["issue_types"]


def test_repeat_ask_and_wrong_status():
    assert case_governance.repeat_asks(["fiddler trace"], "Could you share a Fiddler trace?") == ["fiddler trace"]
    chk = case_governance.check_status("I'm checking with our internal team.", "Pending Customer", False, False)
    assert not chk["ok"] and chk["expected"] == "Pending Internal"


def test_defect_watch_alerts_on_fix():
    alerts = case_governance.defect_watch(
        [{"case_id": "C1", "owner": "e1", "status": "Accepted Defect", "jira": "JIRA-4502"}], {"JIRA-4502": "fixed"})
    assert alerts and alerts[0]["case_id"] == "C1"


def test_meeting_commitment_extracted_and_swarm_nudges():
    items = commitments.extract_commitments("Let's meet Tuesday at 10:00 am ET to troubleshoot.")
    assert items and items[0]["type"] == "meeting"
    now = datetime(2026, 9, 1, 12)
    nudges = commitments.swarm_inbox([{"id": "S1", "engineer": "e1", "opened_at": now - timedelta(hours=3), "replied_at": None}], now)
    assert nudges[0]["to"] == "swarm_duty_lead"


def test_log_analysis_signature():
    r = log_analysis.analyze("connector", "ORA-12154: TNS:could not resolve the connect identifier specified")
    assert r["top_signature"] == "ORA_12154"


def test_copilot_end_to_end_is_audited_and_blocks_customer_actions():
    case = {"case_id": "T1", "subject": "Proxy 407", "body": "We attached the Fiddler trace.", "country": "US",
            "severity": 3, "product": "client", "provided_artifacts": ["fiddler trace"],
            "logs": [{"type": "har", "content": '{"entries":[{"response":{"status":407}}]}'}]}
    s = run_copilot(case, draft="Please share the Fiddler trace.", chosen_status="Pending Customer")
    assert s["panel"]["repeat_asks"] == ["fiddler trace"]
    assert s["panel"]["logs"][0]["top_signature"] == "PROXY_AUTH_407"
    assert "compose_assist:send_customer_reply" in s["blocked_actions"]
    assert s["audit"].verify()
