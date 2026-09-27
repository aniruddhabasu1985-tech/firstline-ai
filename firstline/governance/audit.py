"""
Tamper-evident audit log.

Why: an AI system that influences customer communication and case state must
be able to answer, months later, "what did the AI suggest, what did the
engineer do, and why?" An editable local log (a common first-prototype
design) cannot answer that credibly — anyone can change past entries.

How: every event is hash-chained (each entry stores the SHA-256 of the
previous entry). Altering or deleting any past entry breaks verification of
every entry after it. In production the chain is written to append-only
storage (object-lock / WORM bucket); this module is the verification logic.
The log records metadata and decisions, never full customer message bodies,
so it does not itself become a PII store.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, UTC


class AuditLog:
    def __init__(self):
        self.entries: list[dict] = []

    def record(self, case_id: str, agent: str, event: str, detail: dict, actor: str = "system") -> dict:
        prev = self.entries[-1]["hash"] if self.entries else "GENESIS"
        body = {
            "ts": datetime.now(UTC).isoformat(),
            "case_id": case_id, "agent": agent, "event": event,
            "actor": actor, "detail": detail, "prev_hash": prev,
        }
        body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
        self.entries.append(body)
        return body

    def verify(self) -> bool:
        prev = "GENESIS"
        for e in self.entries:
            body = {k: v for k, v in e.items() if k != "hash"}
            if body["prev_hash"] != prev:
                return False
            if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True
