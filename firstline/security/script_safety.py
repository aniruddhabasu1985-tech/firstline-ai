"""
Script Safety Guardrail (addresses problem P13).

Why: well-meaning engineers sometimes share PowerShell/Python/SQL/shell
scripts with customers to "fix" an issue quickly. Without review, a script
that deletes files, drops tables or rewrites config on a production server
can destroy customer data — turning a Severity-3 ticket into an executive
escalation and, in some contracts, a liability event.

How: deterministic static analysis runs FIRST (free, instant, explainable).
It classifies each script as BLOCK / REVIEW / ALLOW by detecting destructive,
irreversible, privilege-escalating or network-exfiltrating operations, and
checks for the safety practices a reviewer would expect (dry-run flags,
backups, confirmation prompts). An LLM is called only to write a plain-
English risk explanation for flagged scripts — never to decide the verdict.
A BLOCK can only be overridden by a named Core/senior approver (see
governance/policy.py), and the override is written to the audit log.
"""

from __future__ import annotations
import re

DESTRUCTIVE = [
    (r"\bRemove-Item\b|\bdel\s+/[sq]|\brmdir\b|\brd\s+/s", "File/directory deletion"),
    (r"\bfind\b.*\s-delete\b|\bfind\b.*-exec\s+rm\b", "Bulk file deletion via find"),
    (r"\brm\s+-rf?\b", "Recursive file deletion"),
    (r"\bshutil\.rmtree\b", "Recursive directory deletion"),
    (r"\bos\.remove\b|\bos\.unlink\b", "File deletion"),
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", "Drops database objects"),
    (r"\bTRUNCATE\s+TABLE\b", "Truncates table data"),
    (r"\bDELETE\s+FROM\s+\w+\s*;", "DELETE without WHERE clause"),
    (r"\bFormat-Volume\b|\bmkfs\b", "Formats a disk"),
    (r"\bClear-Content\b", "Erases file contents"),
    (r"\bdb\.\w+\.(drop|deleteMany)\(\s*\{?\s*\}?\s*\)", "Unfiltered collection wipe"),
]
PRIVILEGE = [
    (r"Set-ExecutionPolicy\s+(Unrestricted|Bypass)", "Disables script execution policy"),
    (r"\bsudo\b", "Runs with elevated privileges"),
    (r"Stop-Service|Restart-Service|systemctl\s+(stop|restart)", "Stops/restarts services"),
    (r"Set-ItemProperty\s+.*HK(LM|CU)", "Modifies Windows registry"),
    (r"\bUPDATE\s+\w+\s+SET\b(?![\s\S]*\bWHERE\b)", "UPDATE without WHERE clause"),
]
EXFIL = [
    (r"Invoke-WebRequest|Invoke-RestMethod|\bcurl\b|\bwget\b|requests\.(post|put)", "Sends data over the network"),
]
SAFETY_PRACTICES = [
    (r"-WhatIf\b|--dry-run|dry_run\s*=\s*True", "dry-run mode"),
    (r"(?i)backup|Copy-Item.*\.bak|shutil\.copy", "backup step"),
    (r"-Confirm\b|input\(|Read-Host", "confirmation prompt"),
]


# v1.1 design change after held-out eval (see docs/eval-report.md):
# the guard now FAILS CLOSED. A script is ALLOWed only if every line is a
# recognized read-only operation. Anything unrecognized defaults to REVIEW.
READ_ONLY_LINE = re.compile(
    r"^\s*(#|--|$|(Get|Select|Test|Measure|Where|Format|Write-Output|Sort|Group)-?\w*\b"
    r"|SELECT\b|SHOW\b|DESCRIBE\b|EXPLAIN\b"
    r"|(cat|ls|head|tail|grep|wc|df|du|ps|whoami|hostname|ipconfig|nslookup|ping)\b)", re.I)


def _read_only(script: str) -> bool:
    segments = [seg for line in script.splitlines() for seg in re.split(r"\|", line)]
    return all(READ_ONLY_LINE.match(seg.strip()) for seg in segments)


def assess(script: str) -> dict:
    findings = []
    for group, rules in (("destructive", DESTRUCTIVE), ("privilege", PRIVILEGE), ("network", EXFIL)):
        for pattern, label in rules:
            if re.search(pattern, script, re.IGNORECASE):
                findings.append({"category": group, "issue": label})
    practices = [label for p, label in SAFETY_PRACTICES if re.search(p, script)]

    has_destructive = any(f["category"] == "destructive" for f in findings)
    if has_destructive and not {"backup step", "dry-run mode"} & set(practices):
        verdict = "BLOCK"
    elif findings:
        verdict = "REVIEW"
    elif _read_only(script):
        verdict = "ALLOW"
    else:
        verdict = "REVIEW"   # fail closed: unrecognized operations get a human look
    return {"verdict": verdict, "findings": findings, "safety_practices_present": practices}
