# 06 · RAG Design — Unified Knowledge

## The problem RAG solves here

Answers already exist but are split across a knowledge base, a defect tracker, a wiki and thousands of closed cases — and engineers search with the customer's words, not the product's vocabulary. RAG here is less about "chatting with documents" and more about **one search surface that bridges a vocabulary gap and never misses a known defect**.

## Pipeline

| Stage | v1 (this repo) | Production | Why |
|---|---|---|---|
| Sources | KB, defect tracker, wiki, closed cases (one normalized corpus) | Same, synced nightly + on change via APIs | One surface instead of four |
| Chunking | Whole article (articles are short) | Section-level chunks for long runbooks; closed cases summarized to problem/cause/fix before indexing | Raw case threads are noisy and contain PII — index the resolution, not the conversation |
| Query understanding | Domain synonym expansion | Synonym map + a budget-model query rewrite for vague descriptions | Bridges "can't log in" → "SAML authentication" |
| Retrieval | BM25 (lexical) | **Hybrid**: BM25 + dense embeddings in pgvector, fused with reciprocal rank fusion | Lexical catches exact error codes (1603, IM002); dense catches paraphrase ("wizard rolls back") |
| Filtering | Deployment (on-prem / cloud) | + product area, version range, region | Stops cloud fixes being suggested for on-prem problems |
| Reranking | — | Lightweight cross-encoder reranker on top-20 | Cheap precision boost before synthesis |
| Synthesis | — (returns ranked, cited results) | Mid-tier model writes a short answer **only from retrieved text, with citations** | No citation → no answer |
| Known-defect check | Top hit is a defect → surfaced with workaround and status | Same | The most expensive miss to make |

## Why not a dedicated vector database?

The corpus is thousands of documents. PostgreSQL with pgvector handles that comfortably, and the team already needs Postgres for application data and audit metadata. A second database would add cost, another vendor review and another thing to operate, for no measurable gain at this scale.

## Evidence from the held-out eval

Lexical retrieval hit the right document in the top 3 for **83%** of held-out, paraphrased queries. The miss — "setup wizard rolls back at the end" failing to match the installer-error article — is precisely a vocabulary gap that dense embeddings are designed to close. It stays unfixed in v1 on purpose, as evidence for the hybrid design rather than a rule patched to the test.

## Knowledge capture loop (P9)

```
Case resolved → summarize problem + fix → search corpus
   ├─ strong match exists → link case to article (reuse metric)
   └─ weak / no match     → draft article → knowledge team review queue → publish
```

The two-person knowledge team moves from chasing engineers to reviewing drafts — a queue they control.
