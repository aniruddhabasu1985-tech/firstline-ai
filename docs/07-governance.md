# 07 · Governance Layer

## Why governance is a layer, not a feature

These agents influence what enterprise customers read and how their cases are handled. Without explicit governance, three things go wrong: an AI suggestion becomes an action nobody approved; nobody can reconstruct why something happened; and accuracy drifts silently as products and models change. The governance layer exists so every one of those is prevented or detectable — in code, not in a policy document.

## 1. Autonomy levels (who is allowed to do what)

| Level | Meaning | Agents |
|---|---|---|
| L0 Observe | Read and analyze only | — |
| L1 Suggest | Show suggestions to the engineer | Routing, Knowledge, Case Governance, Log Analysis, Script Guard |
| L2 Draft | Prepare a draft the engineer must approve | Compose Assist, Knowledge Capture |
| L3 Act (low-risk, internal) | Take a reversible internal action, logged | Commitment Tracker (reminders only) |
| L4 Act (customer-visible) | Send, change status, close, share scripts | **No agent** |

Enforced in `firstline/governance/policy.py` and verified by a test that fails if any agent can ever send a reply, change status, close a case or share a script.

## 2. Human-in-the-loop by design

- Nothing reaches a customer without an engineer's click.
- Status changes are suggested with a reason; the engineer applies them.
- Script BLOCK verdicts can be overridden only by a senior role, with the override logged.
- KB drafts are published only after knowledge-team review.

## 3. Tamper-evident audit trail

Every suggestion, warning, verdict and override is written to a **hash-chained log**: each entry carries the hash of the previous one, so editing or deleting any past entry breaks verification of everything after it. Production writes to append-only (object-lock) storage. The log stores metadata and decisions — never full customer message bodies — so it doesn't become a PII store itself.

**Use policy:** the audit trail is for quality improvement and incident reconstruction, *not* individual disciplinary scoring. Engineers adopt tools they trust; they avoid tools used to catch them out.

## 4. Evaluation gates (model risk management)

| Gate | Requirement |
|---|---|
| Pre-release | Every prompt, rule or model change passes the eval suite in CI; safety metrics are hard gates (destructive scripts auto-allowed must equal 0) |
| Held-out | Accuracy reported on data never used for tuning; dev-set scores alone never justify release |
| Pilot | Live shadow mode: suggestions logged, measured against engineer decisions, before they're shown |
| Production | Weekly sampled review of suggestions; monthly accuracy report; drift alerts when acceptance rate drops |

## 5. Change control

Model or vendor changes require: eval pass → security sign-off (data terms) → staged rollout by queue. Every task has a cross-vendor fallback, so a vendor change is a configuration change, not a rebuild.

## 6. Alignment with recognized frameworks

- **NIST AI Risk Management Framework** — Govern / Map / Measure / Manage map onto this doc's policy, problem mapping, eval gates and incident process.
- **ISO/IEC 42001** (AI management systems) — defined roles, documented risk controls and continual improvement cycles.
- **EU AI Act** transparency expectations for AI interacting with EU customers — no AI-generated text reaches a customer without human review, and disclosure wording is configurable per region.

## 7. Incident response

If an agent suggestion contributes to a customer-impacting error: disable the specific agent via feature flag (others keep running) → reconstruct from the audit chain → root-cause → add the case to the eval set → re-release through the gates.
