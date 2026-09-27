# 02 · Problem Statements — Why and How for Each

Thirteen problems, grouped into seven agents. Grouping is deliberate: several problems share a root cause, and one well-scoped agent per root cause is easier to govern, test and maintain than thirteen point solutions.

Format for each: **Symptom → Why it matters → Root cause → How FirstLine solves it → KPI moved → How we'll know.**

---

### P1 · Language comprehension and written English
- **Symptom:** Engineers misread what the customer is actually asking; replies contain phrasing native speakers misinterpret; grammar errors.
- **Why it matters:** The case goes in the wrong direction on day one. Every misread adds a round trip, and tone that reads as abrupt costs CSAT even when the fix is right.
- **Root cause:** Strong troubleshooters writing in a second language, under time pressure, with no feedback loop before sending.
- **How:** *Compose Assist* works both directions. **Inbound:** extracts every explicit question from the customer's message and can explain it in the engineer's native language. **Outbound:** flags phrasing native speakers commonly misread ("do the needful", "revert back", "kindly", vague "we will update you") with a concrete rewrite, and flags customer questions the draft leaves unanswered.
- **KPI:** CSAT, FDR (fewer clarification loops). **Measure:** clarification-loop count per case; CSAT verbatims mentioning communication.

### P2 · Knowledge scattered across four systems
- **Symptom:** Engineers search the KB, the defect tracker, the wiki and old cases separately — often with the wrong keywords — and miss existing answers, including known defects.
- **Why it matters:** Days spent re-diagnosing something already documented. Missing a known defect is the most expensive miss in support.
- **Root cause:** No single search surface, and a vocabulary gap between how customers describe symptoms and how articles are titled.
- **How:** *Unified Knowledge* — one retrieval layer across all four sources, query expansion from a domain synonym map (bridging the vocabulary gap), deployment-aware filtering (on-prem vs cloud), mandatory citations, and immediate known-defect surfacing with workaround. See [06-rag-design.md](06-rag-design.md).
- **KPI:** FDR, Elevation %. **Measure:** time-to-first-relevant-article; share of cases linked to an existing article.

### P3 · Asking for information the customer already provided
- **Symptom:** Engineers ask for logs, traces or versions the customer already attached.
- **Why it matters:** It tells the customer nobody read their message, resets their clock, and adds a full round trip. It's among the most damaging CSAT events.
- **Root cause:** Long threads, attachments not surfaced, no pre-send check.
- **How:** *Case Governance* compares artifacts already provided (attachments + thread mentions) with what the draft asks for, and warns before sending. Semantic matching (e.g. "build number" = "version") uses a mid-tier model where keywords are inconclusive.
- **KPI:** CSAT, TTR. **Measure:** repeat-ask rate in QA audit.

### P4 · Wrong case status
- **Symptom:** "Pending Customer" set when the work is internal (triggering chaser emails to a customer waiting on *us*); "Hold" set without a customer request, after which the case is forgotten.
- **Why it matters:** Status drives automation and SLA reporting. Wrong status irritates customers and hides aging cases.
- **Root cause:** Status chosen by habit, not derived from what the reply actually says.
- **How:** *Case Governance* infers the correct status from the draft (internal work → Pending Internal; request to customer → Pending Customer; Hold only when the customer asked to pause; Accepted Defect only with a linked defect) and flags mismatches with the reason. Aging Hold cases without a customer request are surfaced to leads.
- **KPI:** CSAT, TTR. **Measure:** status-mismatch rate; count of Hold cases > N days without customer request.

### P5 · Missed meetings and customer messages
- **Symptom:** Scheduled live sessions missed; customer replies not seen in time.
- **Why it matters:** A missed meeting undoes weeks of goodwill in a B2B relationship.
- **Root cause:** Commitments live in email text, not in any system that reminds anyone.
- **How:** *Commitment & Swarm Tracker* extracts meetings and "I'll update you by…" promises and creates internal reminders — the only automatic action any agent may take (low-risk, reversible, logged). Customer messages unanswered past SLA are flagged.
- **KPI:** CSAT, Average Follow-up Time. **Measure:** missed-commitment count.

### P6 · Generic answers pasted from general-purpose chatbots
- **Symptom:** Replies full of boilerplate ("general troubleshooting steps", "restart your computer") with nothing specific to the customer's environment.
- **Why it matters:** Enterprise IT teams recognize generic text instantly; it signals nobody engaged with their problem.
- **Root cause:** Engineers using a general chatbot with no access to case context, knowledge or logs.
- **How:** *Compose Assist* flags boilerplate and low-specificity drafts, and the replacement it offers is grounded in the case's own logs, knowledge hits and customer questions — the thing a general chatbot can't do.
- **KPI:** CSAT. **Measure:** QA audit score on specificity.

### P7 · Swarm timing and slow swarm follow-through
- **Symptom:** Engineers don't know when to ask seniors for help; seniors reply late; replies go unread when an engineer has several swarms open.
- **Why it matters:** Too early wastes senior time; too late wastes the customer's. Unread replies waste both.
- **Root cause:** Swarm decisions made on gut feel; no tracking of open swarms.
- **How:** A transparent swarm-score rule (case age, attempts, no knowledge match, severity, frustration) tells the engineer *when* to swarm. A swarm inbox nudges the duty lead when a swarm is unanswered past SLA and nudges the engineer when a reply is unread.
- **KPI:** Elevation %, TTR. **Measure:** swarm response time; swarms per 100 cases; swarm-to-elevation ratio.

### P8 · Slow log analysis
- **Symptom:** Many artifact types (network traces, PowerShell, installer, service, connector, event logs…) each read manually.
- **Why it matters:** The single biggest drag on FDR.
- **Root cause:** No tooling; knowledge of failure signatures lives in senior engineers' heads.
- **How:** *Log Analysis* — a parser per log type plus a signature library mapping known failure patterns to cause, reference article and next step. Only unrecognized lines go to a model. New signatures come from resolved cases. See the "rifle not tank" rationale in [05-model-selection.md](05-model-selection.md).
- **KPI:** FDR, Elevation %. **Measure:** time from log upload to first hypothesis.

### P9 · New issues never reach the knowledge base
- **Symptom:** Engineers solve new issues but don't tell the two-person knowledge team; the knowledge team can't chase everyone.
- **Why it matters:** The same problem gets re-diagnosed from scratch next month.
- **Root cause:** Not in anyone's KPI, and engineers can't tell what's "new" because every environment differs.
- **How:** On resolution, *Unified Knowledge* checks whether the fix is already covered. If not (novelty), it drafts an article into the knowledge team's review queue. Capture becomes a review task, not a hunt.
- **KPI:** FDR (long-term). **Measure:** new articles per month from case drafts; reuse rate.

### P10 · No value-added support
- **Symptom:** Tickets closed without sharing best practices or relevant features.
- **Why it matters:** Retention and expansion are driven by the relationship, not just the fix.
- **How:** *Compose Assist* suggests one relevant best-practice tip per reply, based on product area — optional, engineer decides.
- **KPI:** CSAT, retention (upside). **Measure:** tip inclusion rate; CSAT on tip vs no-tip replies.

### P11 · Misrouting by region, language and complexity
- **Symptom:** Routing by product category and severity only; cases land with engineers in the wrong time zone or who don't read the customer's language.
- **Why it matters:** Reassignment hops hurt first response and set a bad first impression.
- **How:** *Smart Routing* adds region (from country), detected language and licensing intent. Deterministic rules first; a budget model only for ambiguous language or intent (e.g. "renew our certificate" is not a licensing renewal). It recommends; the routing platform applies after pilot validation.
- **KPI:** TTFR, CSAT. **Measure:** reassignment rate.

### P12 · Accepted-defect cases forgotten after the fix ships
- **Symptom:** Defect fixed months later; nobody goes back to the customer.
- **Why it matters:** The customer who waited longest gets the worst ending.
- **How:** *Case Governance* defect watcher monitors linked defect tickets and alerts the case owner with a draft update when the fix is released.
- **KPI:** CSAT. **Measure:** days from fix release to customer notification.

### P13 · Unsafe scripts shared with customers
- **Symptom:** Scripts that delete data or change production config shared without review, causing data loss and major escalations.
- **Why it matters:** One incident can outweigh a year of good service.
- **How:** *Script Guard* — deterministic static analysis, **fail-closed**: only provably read-only scripts are allowed; destructive operations without backup/dry-run are blocked; anything unrecognized goes to human review. Blocks can only be overridden by a senior role, logged to the tamper-evident audit trail. See [08-security.md](08-security.md).
- **KPI:** Script incidents (target zero). **Measure:** scripts reviewed / blocked / overridden.

---

## Coverage of the two KPI gaps

| KPI gap | Main drivers | Mechanism |
|---|---|---|
| **FDR** (10% → 50%) | Unified Knowledge, Log Analysis, Case Governance | Right answer faster; fewer wasted round trips |
| **Elevation %** (7% → ≤5%) | Unified Knowledge, Log Analysis, Commitment & Swarm Tracker | L1 resolves more independently; swarms used at the right time instead of premature escalation |
