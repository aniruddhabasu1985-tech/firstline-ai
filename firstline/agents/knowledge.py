"""
Agent 2 — Unified Knowledge (problems P2 scattered knowledge, P9 no KB capture).

Why (P2): the answer often already exists — in a KB article, an open Jira
defect, a Confluence runbook, or a previously solved case — but it's spread
across four systems, and engineers who don't know the product's vocabulary
don't know the keywords to search with. Missing a known defect means days
of troubleshooting something engineering already documented.

How (P2): one retrieval layer over all four sources, with
  - query expansion from a domain synonym map (turns "can't log in" into
    "authentication SSO SAML 401"), which is exactly the vocabulary gap;
  - metadata filtering by deployment (on-prem vs cloud) so cloud answers
    don't get suggested for on-prem problems;
  - known-defect surfacing: if the best match is a Jira defect, the engineer
    is told immediately, with its workaround and status;
  - mandatory citations: no source, no suggestion.
Retrieval here is BM25 (lexical); production adds dense embeddings and a
reranker (hybrid search) — see docs/06-rag-design.md.

Why (P9): knowledge workers can't chase every engineer to find new issues,
and engineers can't tell what's "new" because every environment differs.
How (P9): when a case is resolved, the agent checks whether the resolution
is already covered by the corpus. If the best match is weak (novelty), it
drafts a KB article for knowledge-worker review. This turns knowledge
capture from a manual hunt into a review queue.
"""

from __future__ import annotations
import json
import math
import re
from collections import Counter
from pathlib import Path

SYNONYMS = {
    "login": "authentication sso saml signin", "log": "logs", "can't": "cannot fail",
    "slow": "performance latency", "sso": "saml authentication", "cert": "certificate",
    "times": "timeout", "timeout": "timed", "stuck": "queued hang", "jobs": "schedules scheduled",
    "crashes": "crash memory leak", "install": "installer msi", "msi": "installer 1603",
    "rows": "data dropped missing", "proxy": "407", "unauthorized": "401 token",
    "blank": "certificate tls chain", "dsn": "odbc driver", "tns": "ora oracle",
}
_TOKEN = re.compile(r"[a-z0-9']+")


def _tok(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def expand(query: str) -> list[str]:
    toks = _tok(query)
    out = list(toks)
    for t in toks:
        if t in SYNONYMS:
            out += _tok(SYNONYMS[t])
    return out


class UnifiedKnowledge:
    def __init__(self, corpus_path: str | Path | None = None, k1: float = 1.4, b: float = 0.75):
        path = corpus_path or Path(__file__).resolve().parents[2] / "data" / "knowledge_corpus.json"
        self.docs = json.loads(Path(path).read_text())
        self.k1, self.b = k1, b
        self._index()

    def _index(self):
        self.doc_toks = [_tok(d["title"] + " " + d["title"] + " " + d["body"]) for d in self.docs]
        self.avgdl = sum(map(len, self.doc_toks)) / len(self.doc_toks)
        df = Counter(t for toks in self.doc_toks for t in set(toks))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _score(self, q: list[str], i: int) -> float:
        toks = self.doc_toks[i]
        tf = Counter(toks)
        s = 0.0
        for t in q:
            if t in tf:
                f = tf[t]
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(toks) / self.avgdl))
        return s

    def search(self, query: str, deployment: str = "any", k: int = 3) -> list[dict]:
        q = expand(query)
        results = []
        for i, d in enumerate(self.docs):
            if deployment != "any" and d["deployment"] not in (deployment, "any"):
                continue
            s = self._score(q, i)
            if s > 0:
                results.append({"id": d["id"], "source": d["source"], "title": d["title"], "score": round(s, 2),
                                "status": d.get("status")})
        results.sort(key=lambda r: -r["score"])
        return results[:k]

    def known_defect(self, query: str, deployment: str = "any") -> dict | None:
        hits = self.search(query, deployment, k=1)
        if hits and hits[0]["source"] == "jira":
            return hits[0]
        return None

    def is_novel(self, resolution_summary: str, threshold: float = 6.0) -> bool:
        hits = self.search(resolution_summary, k=1)
        return not hits or hits[0]["score"] < threshold

    def draft_kb_article(self, case_id: str, problem: str, resolution: str) -> dict:
        return {"status": "DRAFT_PENDING_KNOWLEDGE_WORKER_REVIEW", "source_case": case_id,
                "title": problem[:90], "symptoms": problem, "resolution": resolution,
                "reviewer_checklist": ["Remove customer-identifying details", "Confirm environment scope",
                                       "Confirm not a duplicate", "Tag product area and deployment"]}
