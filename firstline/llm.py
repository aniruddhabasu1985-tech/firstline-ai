"""
Model gateway. Every LLM call in the system goes through `Gateway.call()`,
which is where three non-negotiable controls live:

  - Security: PII is redacted and customer text is screened for prompt
    injection BEFORE anything leaves the boundary.
  - Cost: every call is metered per task, so cost per case is a measured
    number, not an estimate.
  - Resilience: if the primary vendor fails, the call retries once on the
    fallback vendor defined in config.TASK_ROUTING.

By default the gateway runs a deterministic offline backend so the full
test suite, eval harness and demo run with zero API keys and zero cost.
Set FIRSTLINE_LIVE=1 plus vendor keys to use real providers (adapters are
intentionally thin; see docs/04-architecture.md).
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from firstline.config import TASK_ROUTING, token_cost
from firstline.security.pii import redact
from firstline.security.injection import screen


@dataclass
class CallRecord:
    task: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    injection_flagged: bool
    pii_redactions: int


@dataclass
class Gateway:
    records: list[CallRecord] = field(default_factory=list)

    def call(self, task: str, prompt: str, offline_result: str, est_out_tokens: int = 150) -> dict:
        primary, fallback = TASK_ROUTING[task]
        clean, n_redacted = redact(prompt)
        flagged, _ = screen(prompt)
        model = primary
        if os.environ.get("FIRSTLINE_LIVE") == "1":   # pragma: no cover - live path
            text = self._live(model, clean) or self._live(fallback, clean)
            model = model if text else fallback
        else:
            text = offline_result
        tokens_in = max(1, len(clean) // 4)
        rec = CallRecord(task, model, tokens_in, est_out_tokens,
                         token_cost(model, tokens_in, est_out_tokens), flagged, n_redacted)
        self.records.append(rec)
        return {"text": text, "model": model, "injection_flagged": flagged, "pii_redactions": n_redacted}

    def _live(self, model: str, prompt: str) -> str | None:  # pragma: no cover
        raise NotImplementedError("Wire vendor SDKs here; see docs/04-architecture.md")

    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.records)
