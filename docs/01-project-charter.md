# 01 · Project Charter (DMAIC — Define)

## Why DMAIC, and why Agile inside it

This is an **operations improvement program**, not a software feature. It starts from a measured defect rate in live support work and has to prove it moved business KPIs — so the governing method is **Lean Six Sigma DMAIC** (Define → Measure → Analyze → Improve → Control), the recognized standard for data-driven process improvement with a quantified baseline.

DMAIC is deliberately weak at one thing: shipping software iteratively. So the **Improve** phase is delivered as **Agile (Scrum, 2-week sprints)**, with each agent released behind feature flags and evaluation gates. DMAIC owns *what success means and whether we got there*; Agile owns *how the build ships*. This hybrid is common in enterprise transformation, and it's the right fit here because the business case needs Six Sigma rigor while the AI components need fast iteration against evals.

| Phase | Output in this repo |
|---|---|
| Define | This charter, SIPOC, CTQ tree, scope, stakeholders |
| Measure | Baseline KPIs and miss taxonomy — [03-measure-analyze.md](03-measure-analyze.md) |
| Analyze | Root causes per problem — [02-problem-statements.md](02-problem-statements.md) |
| Improve | Seven agents + governance + security layers (the code), delivered in sprints — [10-delivery-plan.md](10-delivery-plan.md) |
| Control | Eval gates, KPI dashboard, audit log, drift monitoring — [07-governance.md](07-governance.md) |

## Problem statement

An outsourced Tier-1 (L1) technical support team serving enterprise B2B customers of a data-analytics SaaS platform meets most of its KPIs but misses two that matter most to customers and to cost: **First Day Resolution (FDR)** runs far below target, and **Elevation %** (cases escalated to the onshore Core team) runs above target. A sample audit of closed cases found that a significant share (illustratively ~30%) contained at least one *preventable* miss — repeat requests for information already provided, wrong case status, generic or unclear replies, missed commitments, slow log analysis, or unsafe advice.

Every case is non-generic — each customer environment (on-prem or cloud, servers, desktop clients, data connectors) is different — so the fix is not "more scripts." It's giving engineers the right knowledge, analysis and guardrails *at the moment they work a case*.

## Goal statement (SMART)

| KPI | Baseline (illustrative) | Target | By |
|---|---|---|---|
| First Day Resolution | 10% | 30% pilot → 50% steady state | Pilot end → +2 quarters |
| Elevation % to Core | 7% | ≤ 5% | Pilot end |
| Preventable-miss rate in audited cases | ~30% | ≤ 10% | +2 quarters |
| CSAT | At target (≥ 90%) | Hold or improve | Continuous |
| Time to First Response | At target | Improve via correct routing | Pilot end |
| Destructive scripts shared without senior review | Non-zero | **Zero** | Day 1 of go-live |

## SIPOC

| Suppliers | Inputs | Process | Outputs | Customers |
|---|---|---|---|---|
| Customers (IT & data teams) | Case description, logs, traces, screenshots | Case opened → skill-based routing → L1 troubleshoots → resolve or elevate → Core/engineering for defects | Resolution, KB article, defect ticket | End customers |
| Knowledge base, defect tracker, wiki | Known issues, runbooks, defects | Swarm to seniors when stuck | Updated knowledge | Client (the SaaS vendor) |
| Onshore Core team | Senior guidance | Accepted-defect wait → fix → customer update | Closed case, CSAT | Service provider |

## CTQ tree (Critical to Quality)

```
Customer need: "Fix my problem fast, without making me repeat myself"
├── Understood the first time      → Compose Assist (intent explainer), Smart Routing (language)
├── Right answer fast              → Unified Knowledge, Log Analysis
├── No wasted effort               → Case Governance (repeat asks, status, live-session trigger)
├── Promises kept                  → Commitment & Swarm Tracker
└── Safe advice                    → Script Guard
```

## Scope

**In scope:** L1 and licensing queues; case intake, drafting, status, swarm and defect-follow-up workflows; knowledge capture into the knowledge team's review queue.
**Out of scope (v1):** autonomous customer replies, auto-closing cases, changes to the core team's own workflow, voice channels.

## Stakeholders

| Role | Interest | Engagement |
|---|---|---|
| Client support leadership | Customer experience, Core capacity, cost | Sponsor; approves go/no-go gates |
| Onshore Core team | Fewer, better-prepared escalations; less swarm load | Co-designs swarm rules; reviews escalation quality |
| L1 engineers | Less rework, clearer guidance | Pilot cohort; feedback every sprint |
| Knowledge team | Faster capture of new issues | Owns KB draft review queue |
| IT security / data protection | Data handling, vendor risk | Approves security gate before live data |
| Provider delivery leadership | Margin, account health | Co-sponsor; co-invests in build |

## RACI (key decisions)

| Decision | Client support lead | Provider delivery lead | Core team lead | Security | Project manager |
|---|---|---|---|---|---|
| Go/no-go per phase | A | R | C | C | R |
| Escalation & swarm rules | C | C | A/R | I | R |
| Security approval | I | C | I | A/R | R |
| Model/vendor change | C | C | I | A | R |
| KB article publication | I | I | C | I | Knowledge team A/R |

*R = Responsible, A = Accountable, C = Consulted, I = Informed.*
