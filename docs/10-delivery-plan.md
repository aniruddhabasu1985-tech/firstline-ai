# 10 · Delivery Plan — Agile Inside DMAIC

## Release strategy: highest ROI and lowest risk first

The order isn't "build all seven, launch." Each release must earn the next one through a go/no-go gate.

| Release | Agents | Why this order |
|---|---|---|
| **R1** (Sprints 1–3) | Script Guard, Case Governance (repeat ask + status), Smart Routing | Mostly deterministic → low model risk; Script Guard removes the highest-severity risk on day one; status/repeat fixes are the most visible CSAT wins |
| **R2** (Sprints 4–6) | Unified Knowledge, Log Analysis | Biggest FDR and Elevation levers; need the knowledge sync and signature library built first |
| **R3** (Sprints 7–8) | Compose Assist, Commitment & Swarm Tracker, Knowledge Capture | Depend on R2's knowledge layer; change engineer habits, so they follow trust built in R1–R2 |

## Sprint cadence (Scrum, 2-week sprints)

- Sprint planning with the pilot cohort's lead; backlog items traced to a problem ID (P1–P13) and a KPI.
- Definition of Done: code + tests + **eval pass on held-out data** + security checklist + docs updated.
- Sprint review with Core and L1 representatives in the same room — both sides see the same numbers.
- Retrospective feeds the eval set: every false alarm or miss becomes a new test case.

## Pilot design

| Element | Design |
|---|---|
| Cohort | 4–5 L1 engineers + 1 lead, one region |
| Control | Comparable engineers without the copilot, same period |
| Phase 1 — synthetic | Two weeks on synthetic/replayed cases; no live customer data |
| Phase 2 — shadow | Suggestions logged but not shown; measured against what engineers actually did |
| Phase 3 — assist | Suggestions shown; engineers decide |
| Duration | 8–10 weeks across phases |

## Go / no-go gates

| Gate | Pass criteria |
|---|---|
| Security | Vendor terms, region routing, pen test signed off before any live data |
| Accuracy | Held-out eval thresholds met; destructive scripts auto-allowed = 0 |
| Shadow | Suggestion precision ≥ agreed threshold (e.g. ≥ 80%) per agent; false alarms ≤ agreed rate |
| Pilot outcome | Statistically meaningful improvement vs control on Elevation % and FDR; CSAT not worse |
| Adoption | Suggestion acceptance rate ≥ agreed threshold; engineer feedback net positive |

## RAID log (top items)

| Type | Item | Response |
|---|---|---|
| Risk | Engineers ignore suggestions (alert fatigue) | Precision gates before display; false alarms tracked and pruned every sprint |
| Risk | Audit data used punitively, killing adoption | Written use policy: improvement, not discipline ([07](07-governance.md)) |
| Risk | Model price or availability changes | Cross-vendor fallback per task; token cost is a minor ROI driver |
| Risk | Knowledge base quality limits RAG quality | Knowledge Capture + knowledge team review; stale-article report |
| Assumption | Onshore cost per elevated case | Validated with finance before the business case is finalized (top sensitivity driver) |
| Issue | Integration access to CRM / defect tracker | Read-only service accounts requested in Sprint 0 |
| Dependency | Security review capacity | Booked at charter sign-off, not at release |

## Change management (ADKAR)

- **Awareness** — share the audit findings with the team as a process problem, not a people problem.
- **Desire** — show engineers what they get: fewer re-asks, faster answers, protection from unsafe-script incidents.
- **Knowledge** — 30-minute walkthrough per release; one-page "what each warning means".
- **Ability** — pilot leads coach in the first two weeks of each release.
- **Reinforcement** — celebrate FDR wins; publish KB articles credited to the engineer whose case produced them.

## Control phase — keeping the gains

| Control | Owner | Frequency |
|---|---|---|
| KPI dashboard (FDR, Elevation %, CSAT, repeat-ask rate, status-mismatch rate) | Support lead | Weekly |
| Agent precision / acceptance / false-alarm report | Project manager | Monthly |
| Eval suite in CI on every change | Engineering | Every change |
| Audit-chain verification | Security | Monthly |
| Model price & vendor review | Project manager | Quarterly |
