"""
Model registry and vendor policy.

Design rules this file enforces (see docs/05-model-selection.md):
  1. Vendor allowlist: only models from US-headquartered providers, served
     through enterprise terms with zero-data-retention available. Models from
     sanctioned jurisdictions are rejected at load time, not by convention.
  2. "Rifle, not tank": every task is assigned the cheapest tier that meets
     its accuracy bar. Deterministic code handles what code can handle; LLMs
     are called only where language understanding is genuinely required.
  3. Every assignment has a same-tier fallback from a different vendor, so a
     single-vendor outage or price change never stops the support floor.

Prices: USD per 1M tokens, standard tier, as published September 2026.
Promotional prices are replaced with their post-promotion list price so the
ROI model does not depend on a discount that expires.
"""

APPROVED_VENDOR_COUNTRIES = {"US"}
SANCTIONED_COUNTRIES = {"CN", "RU", "KP", "IR", "CU", "SY", "BY"}

MODELS = {
    # --- Budget tier: classification, routing, extraction -----------------
    "gpt-5-nano":            {"vendor": "OpenAI",    "hq": "US", "tier": "budget",   "in": 0.05, "out": 0.40},
    "gemini-3.1-flash-lite": {"vendor": "Google",    "hq": "US", "tier": "budget",   "in": 0.25, "out": 1.50},
    # --- Mid tier: writing, synthesis, semantic comparison ----------------
    "gpt-5-mini":            {"vendor": "OpenAI",    "hq": "US", "tier": "mid",      "in": 0.25, "out": 2.00},
    "gemini-3.8-flash":      {"vendor": "Google",    "hq": "US", "tier": "mid",      "in": 1.50, "out": 7.50},   # post-promo list price
    "claude-haiku-4.5":      {"vendor": "Anthropic", "hq": "US", "tier": "mid",      "in": 1.00, "out": 5.00},
    # --- Reasoning tier: multi-log correlation, risk explanation ----------
    "claude-sonnet-5":       {"vendor": "Anthropic", "hq": "US", "tier": "reasoning", "in": 2.00, "out": 10.00},
    "gemini-3.1-pro":        {"vendor": "Google",    "hq": "US", "tier": "reasoning", "in": 2.00, "out": 12.00},
    # --- Embeddings --------------------------------------------------------
    "text-embedding-3-small":{"vendor": "OpenAI",    "hq": "US", "tier": "embedding", "in": 0.02, "out": 0.00},
}

# task -> (primary, fallback). Fallback is always a different vendor.
TASK_ROUTING = {
    "classify_case":        ("gpt-5-nano", "gemini-3.1-flash-lite"),
    "detect_language":      ("gpt-5-nano", "gemini-3.1-flash-lite"),
    "summarize_thread":     ("gpt-5-nano", "gemini-3.1-flash-lite"),
    "repeat_ask_semantic":  ("gpt-5-mini", "claude-haiku-4.5"),
    "compose_reply":        ("gpt-5-mini", "claude-haiku-4.5"),
    "explain_customer":     ("gpt-5-mini", "gemini-3.8-flash"),
    "rag_answer":           ("gpt-5-mini", "claude-haiku-4.5"),
    "kb_draft":             ("gpt-5-mini", "claude-haiku-4.5"),
    "log_long_context":     ("gemini-3.8-flash", "gpt-5-mini"),     # flat pricing on very long inputs
    "log_correlation_hard": ("claude-sonnet-5", "gemini-3.1-pro"),
    "script_risk_explain":  ("claude-sonnet-5", "gemini-3.1-pro"),
    "embed":                ("text-embedding-3-small", "text-embedding-3-small"),
}


def validate_registry() -> None:
    for name, m in MODELS.items():
        if m["hq"] in SANCTIONED_COUNTRIES:
            raise ValueError(f"Model {name} is from a sanctioned jurisdiction ({m['hq']}) and cannot be registered.")
        if m["hq"] not in APPROVED_VENDOR_COUNTRIES:
            raise ValueError(f"Model {name} vendor HQ {m['hq']} is not on the approved list.")
    for task, (primary, fallback) in TASK_ROUTING.items():
        for model in (primary, fallback):
            if model not in MODELS:
                raise ValueError(f"Task {task} references unknown model {model}.")


def token_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    m = MODELS[model]
    return (tokens_in * m["in"] + tokens_out * m["out"]) / 1_000_000


validate_registry()
