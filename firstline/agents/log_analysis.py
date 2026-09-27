"""
Agent 6 — Log Analysis (problem P8: slow analysis across many log types).

Why: B2B analytics support involves a long list of artifact types — network
traces (HAR/Fiddler), PowerShell transcripts, installer (MSI) logs, service
and engine logs, connector/driver logs, Windows event logs, and more. Each
has its own format and its own tell-tale failure signatures. Reading them
manually is slow and inconsistent, and it's the single biggest drag on First
Day Resolution.

How — "rifle, not tank":
  1. A parser per log type extracts candidate lines (free, instant).
  2. A signature library maps known failure patterns to a probable cause,
     the matching knowledge article, and the next step. This covers the
     large majority of real cases without any model call.
  3. Only lines that match NO signature go to a model: a long-context mid
     tier for summarization, escalating to the reasoning tier only when the
     engineer asks for multi-log correlation. The model never sees the full
     raw log without PII redaction.
The registry is designed to grow to every artifact type the team handles;
new signatures come from resolved cases via the Knowledge agent.
"""

from __future__ import annotations
import json
import re

SIGNATURES = [
    ("PROXY_AUTH_407", r'"status"\s*:\s*407|\b407\b.*proxy', "Proxy requires authentication", "KB-1007",
     "Add server host to proxy bypass list or configure proxy credentials."),
    ("AUTH_401", r'"status"\s*:\s*401|401 Unauthorized', "Credential/token rejected", "KB-1008",
     "Check token expiry / identity configuration; rotate credentials."),
    ("ACCESS_DENIED", r"Access is denied", "Service account lacks permission", "KB-1001",
     "Grant required rights to the service account and restart the service."),
    ("MSI_1603", r"\b1603\b", "Generic fatal install error", "KB-1006",
     "Reboot, run as admin, exclude install dir from antivirus, review verbose MSI log."),
    ("ODBC_IM002", r"IM002|no default driver specified", "DSN/driver bitness mismatch", "KB-1002",
     "Recreate DSN in 64-bit ODBC administrator; match driver bitness."),
    ("ORA_12154", r"ORA-12154", "Oracle TNS alias not resolvable", "CASE-77012",
     "Set TNS_ADMIN for the service account and restart."),
    ("SAML_SIGNATURE", r"SAML.*signature", "IdP signing certificate mismatch", "KB-1003",
     "Refresh IdP federation metadata / upload new signing certificate."),
    ("MEMORY_OOM", r"OutOfMemory|memory usage .* exceeds", "Worker memory exhaustion", "JIRA-4502",
     "Known defect on long schedules — apply maintenance release; interim: split schedule."),
    ("READ_TIMEOUT", r"Read timed out|SocketTimeoutException", "Query exceeds connector timeout", "KB-1005",
     "Increase connector timeout, enable bulk mode, filter at source."),
    ("TLS_HANDSHAKE", r"Schannel|TLS alert|handshake fail", "TLS handshake failure (cert chain/protocol)", "CASE-77340",
     "Verify full certificate chain and TLS protocol versions on both ends."),
]
_COMPILED = [(sid, re.compile(p, re.I), cause, ref, step) for sid, p, cause, ref, step in SIGNATURES]

PARSERS = {
    "har": lambda text: [json.dumps(e) for e in json.loads(text).get("entries", [])],
    "powershell": lambda text: [l for l in text.splitlines() if l.strip()],
    "msi": lambda text: [l for l in text.splitlines() if re.search(r"error|fail|return value 3", l, re.I)],
    "connector": lambda text: text.splitlines(),
    "server": lambda text: [l for l in text.splitlines() if re.search(r"ERROR|WARN|FATAL|Exception", l)],
    "eventlog": lambda text: text.splitlines(),
}


def analyze(log_type: str, content: str) -> dict:
    parser = PARSERS.get(log_type, lambda t: t.splitlines())
    lines = parser(content)
    findings, unmatched = [], []
    for line in lines:
        hit = next(((sid, cause, ref, step) for sid, rx, cause, ref, step in _COMPILED if rx.search(line)), None)
        if hit:
            sid, cause, ref, step = hit
            findings.append({"signature": sid, "probable_cause": cause, "reference": ref, "next_step": step, "evidence": line[:200]})
        else:
            unmatched.append(line)
    return {"log_type": log_type, "lines_examined": len(lines), "findings": findings,
            "top_signature": findings[0]["signature"] if findings else None,
            "needs_model_review": bool(unmatched) and not findings, "unmatched_lines": len(unmatched)}
