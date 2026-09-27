# 03 · Measure & Analyze

## Baseline KPIs (illustrative)

| KPI | Target | Baseline | Status |
|---|---|---|---|
| CSAT | ≥ 90% / month | At target | ✅ |
| Time to Resolution | ≤ 5 days | At target | ✅ |
| Time to First Response | Per SLA | At target | ✅ |
| Productivity | 50 cases / engineer / month | At target | ✅ |
| Average Follow-up Time | Per case SLA | At target | ✅ |
| **Elevation %** | ≤ 5% | **7%** | ❌ |
| **First Day Resolution** | 50% | **10%** | ❌ |

The team is *busy and compliant* but not *resolving independently*. That pattern — throughput and SLA metrics green, resolution-quality metrics red — usually means engineers are working hard on the wrong things: rework, re-asking, re-searching, waiting.

## Miss taxonomy from the case audit

A sample audit tagged each preventable miss (multi-label; a case can have several). Illustrative Pareto:

| Category | Share of tagged misses | Agent |
|---|---|---|
| Requirement / repeat ask / handoff gaps | Largest | Case Governance, Compose Assist |
| Commitment / response delay | High | Commitment & Swarm Tracker |
| Technical guidance quality (incl. slow log analysis, generic answers) | High | Log Analysis, Unified Knowledge, Compose Assist |
| Status / ownership / closure errors | Medium | Case Governance |
| Meeting / scheduling misses | Medium | Commitment & Swarm Tracker |
| Unsafe advice | Low frequency, highest severity | Script Guard |

## Root-cause analysis (fishbone summary)

- **People:** second-language writing; uncertainty about when to ask seniors.
- **Process:** status chosen by habit; no pre-send check; knowledge capture outside anyone's KPI; no defect-fix follow-up loop.
- **Tools:** four disconnected knowledge sources; no log tooling; routing blind to region and language; general chatbots without case context.
- **Environment:** every customer environment is different, so issues look "new" even when they aren't.
- **Measurement:** throughput KPIs rewarded; resolution-quality misses invisible until audit.

## Lessons from an earlier prototype (v0)

A first attempt used a local browser extension with heuristic rules and no model access. What it taught:
1. **Rule checks catch the obvious misses** (repeat asks, status language) — worth keeping as the cheap first layer.
2. **Rules alone can't understand context** — paraphrases slip through (confirmed again in this repo's held-out eval).
3. **A local, editable log isn't audit-grade** — replaced here with a hash-chained, tamper-evident log.
4. **Engineer-in-the-loop is the right default** — the tool warns, the engineer decides. Kept as the core governance principle.
5. **On-device translation depends on what's installed on each machine** — replaced with a server-side native-language explanation step.
