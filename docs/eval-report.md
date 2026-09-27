# Evaluation Report

Run: `python -m eval.run_eval`. Three sets, reported separately on purpose.

## 1. Development set (written alongside the rules)

All 16 component metrics score 100%. **This is not the headline** — the rules and this set were written together, so it's effectively the training set. It proves the logic does what it says, nothing more.

## 2. Held-out set (written after rules were frozen, never used for tuning)

| Component | Accuracy |
|---|---|
| Status validation | 100% |
| Log signature matching | 100% |
| Smart routing | 83% |
| Knowledge retrieval (hit@3) | 83% |
| Compose issue detection | 67% |
| Repeat-ask detection | 50% |

### Failure analysis

| Miss | Class | Response |
|---|---|---|
| "Help with **renewing** the SSL cert" routed to licensing | Semantic ambiguity | Left unfixed — this is why ambiguous intent goes to a budget-tier model |
| "Setup wizard rolls back" missed the installer-error article | Vocabulary gap | Left unfixed — this is why production retrieval is hybrid (lexical + dense) |
| "Which **build number**…?" not recognized as asking for version | Paraphrase | Left unfixed — semantic repeat-ask check uses a mid-tier model |
| Acknowledging the HAR file flagged as a repeat ask | Context | Same — semantic layer resolves it |
| "Great question! Here are a few things…" not flagged as generic | Paraphrase | Same — model-based boilerplate check |
| A European country missing from the region map | Config gap | **Fixed** (data defect, not a tuning change) |
| Two destructive scripts rated **ALLOW** | **Safety control failing open** | **Redesigned** — see below |

The semantic misses are left in deliberately. Patching rules to pass a held-out set would contaminate it, and these failures are the evidence for the model tiers in the architecture.

## 3. Fresh held-out set for the Script Guard redesign

The script guard originally used a blocklist. After it allowed two destructive scripts, it was redesigned to **fail closed**: only scripts made entirely of recognized read-only operations are allowed; anything unrecognized goes to human review. It was then tested on a new set written after the fix:

| Metric | Result |
|---|---|
| Verdict accuracy | 87.5% |
| Destructive scripts correctly BLOCKED | 67% |
| **Destructive scripts auto-ALLOWED** | **0** ✅ |

The one destructive script not recognized (`rm` without a recursive flag) went to REVIEW — a human sees it before any customer does. For a safety control, that's the metric that matters. The pattern is logged as a backlog item rather than patched against this set.

## Security and governance checks

PII redaction recall 100%, injection detection 100% (dev set), audit chain verified, and a test proving no agent can send, change status, close or share scripts.
