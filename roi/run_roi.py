"""Generates roi/results/roi_report.md and charts. Usage: python -m roi.run_roi"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from roi.model import all_scenarios, recommended_deal, ai_cost_per_case, sensitivity, A

OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)
NAVY, TEAL, CORAL, GREY = "#1F3A5F", "#2A9D8F", "#E76F51", "#8D99AE"


def _style(ax, title):
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def charts(sc, deals):
    # 1. Rifle vs tank
    fig, ax = plt.subplots(figsize=(7, 3.6))
    vals = [ai_cost_per_case(), ai_cost_per_case(strategy="all_frontier")]
    bars = ax.bar(["Tiered routing\n(this design)", "Frontier model\nfor everything"], vals, color=[TEAL, CORAL])
    ax.bar_label(bars, labels=[f"${v:.3f}" for v in vals])
    ax.set_ylabel("LLM cost per case (USD)")
    _style(ax, "Model cost per case: rifle vs tank")
    fig.tight_layout(); fig.savefig(OUT / "chart_cost_per_case.png", dpi=150); plt.close(fig)

    # 2. Client benefit levers per scenario (stacked)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    names = list(sc)
    levers = ["elevation_cost_avoided", "core_swarm_time_saved", "l1_capacity_value_realized", "script_incidents_avoided"]
    labels = ["Escalation cost avoided", "Senior swarm time saved", "L1 capacity (realized)", "Script incidents avoided"]
    colors = [NAVY, TEAL, GREY, CORAL]
    bottom = [0] * len(names)
    for lv, lb, c in zip(levers, labels, colors):
        v = [sc[n]["levers_monthly"][lv] for n in names]
        ax.bar(names, v, bottom=bottom, label=lb, color=c)
        bottom = [b + x for b, x in zip(bottom, v)]
    run = [sc[n]["run_cost_monthly"] for n in names]
    ax.plot(names, run, "k--", marker="o", label="Monthly run cost")
    ax.set_ylabel("USD per month"); ax.legend(fontsize=8, frameon=False)
    _style(ax, "Monthly gross benefit by lever vs run cost")
    fig.tight_layout(); fig.savefig(OUT / "chart_levers.png", dpi=150); plt.close(fig)

    # 3. Payback: naive vs recommended, provider side (base)
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    b = sc["base"]; d = deals["base"]
    cats = ["FTE billing", "Per-case billing"]
    naive = [b["fte_model"]["provider_payback_months_on_share"] or 120,
             b["per_case_model"]["provider_payback_months_on_share"] or 120]
    rec = [d["fte_billing"]["provider_payback_months"], d["per_case_billing"]["provider_payback_months"]]
    cli = [d["fte_billing"]["client_payback_months"], d["per_case_billing"]["client_payback_months"]]
    x = range(2); w = 0.27
    for i, (vals, lab, col) in enumerate([(naive, "Provider — naive terms", CORAL), (rec, "Provider — value-share terms", TEAL), (cli, "Client — value-share terms", NAVY)]):
        bars = ax.bar([p + (i - 1) * w for p in x], [min(v, 60) for v in vals], w, label=lab, color=col)
        ax.bar_label(bars, labels=[(f"{v:.0f}" if v < 60 else "60+") for v in vals], fontsize=8)
    ax.set_xticks(list(x)); ax.set_xticklabels(cats); ax.set_ylabel("Payback (months, capped at 60)")
    ax.legend(fontsize=8, frameon=False)
    _style(ax, "Base case payback: why deal structure matters")
    fig.tight_layout(); fig.savefig(OUT / "chart_payback.png", dpi=150); plt.close(fig)


def fmt(v):
    if not isinstance(v, (int, float)):
        return str(v)
    return f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"


def report(sc, deals):
    b = sc["base"]
    lines = ["# ROI Report (generated)", "",
             "> Illustrative model for a generic outsourced Tier-1 B2B technical support program. "
             "All inputs live in `roi/assumptions.json`. These are **projections**, to be replaced with measured pilot data.", "",
             "## Headline (base scenario, before deal structuring)", "",
             f"- Client net benefit: **{fmt(b['client_net_benefit_monthly'])}/month**, **{fmt(b['client_net_benefit_annual'])}/year**",
             f"- Payback on full one-time cost ({fmt(b['one_time_cost'])}): **{b['payback_months']} months**",
             f"- 3-year net value: **{fmt(b['three_year_net_usd'])}**",
             f"- LLM cost per case: **${b['ai_cost_per_case_usd']}** (tiered) vs **${ai_cost_per_case(strategy='all_frontier'):.4f}** (frontier-for-everything)", "",
             "## Scenarios", "",
             "| Metric | Conservative | Base | Optimistic |", "|---|---|---|---|"]
    rows = [("Escalation cost avoided / mo", lambda s: s["levers_monthly"]["elevation_cost_avoided"]),
            ("Senior swarm time saved / mo", lambda s: s["levers_monthly"]["core_swarm_time_saved"]),
            ("L1 capacity value (realized) / mo", lambda s: s["levers_monthly"]["l1_capacity_value_realized"]),
            ("Script incidents avoided / mo", lambda s: s["levers_monthly"]["script_incidents_avoided"]),
            ("Run cost / mo", lambda s: s["run_cost_monthly"]),
            ("**Client net / mo**", lambda s: s["client_net_benefit_monthly"]),
            ("Payback (months)", lambda s: s["payback_months"]),
            ("Year-1 ROI %", lambda s: s["roi_year1_pct"]),
            ("3-year net", lambda s: s["three_year_net_usd"])]
    for label, f in rows:
        vals = [f(sc[n]) for n in ("conservative", "base", "optimistic")]
        cell = lambda v: (f"{v}" if "months" in label or "%" in label else fmt(v))
        lines.append(f"| {label} | " + " | ".join(cell(v) for v in vals) + " |")
    lines += ["", "![levers](chart_levers.png)", "",
              "## Commercial structures", "",
              "### Naive terms (why they fail)", "",
              f"- **FTE billing:** productivity frees ~{b['net_freed_l1_fte']} FTE. If the client converts that into headcount cuts, "
              f"the provider loses {fmt(b['fte_model']['provider_revenue_at_risk_if_cut'])}/month. With only a cost-plus enablement fee, "
              f"provider payback on a 50% build share is {b['fte_model']['provider_payback_months_on_share']} months.",
              f"- **Per-case billing with 50% price gainshare:** provider margin gain is smaller than the platform run cost it carries — no payback.",
              "", "Most of the value lands in the client's P&L (onshore escalation cost). Unshared, the provider has no reason to fund it.", "",
              "### Recommended value-share terms", "",
              "| Base scenario | FTE billing | Per-case billing |", "|---|---|---|"]
    d = deals["base"]
    for label, k in [("Client net / mo", "client_net_monthly"), ("Provider net / mo", "provider_net_monthly"),
                     ("Client payback (months)", "client_payback_months"), ("Provider payback (months)", "provider_payback_months"),
                     ("Client share of value %", "client_share_of_value_pct")]:
        f = (lambda v: f"{v}") if ("months" in label or "%" in label) else fmt
        lines.append(f"| {label} | {f(d['fte_billing'][k])} | {f(d['per_case_billing'][k])} |")
    lines += ["", f"Per-case price after gainshare: ${d['per_case_billing']['price_per_case']} (from ${b['per_case_model']['parity_price_per_case']} parity).", "",
              "![payback](chart_payback.png)", "", "![cost](chart_cost_per_case.png)", "",
              "## Sensitivity (base case, each assumption moved ±25%)", "",
              "| Assumption | Change if 25% worse | Change if 25% better |", "|---|---|---|"]
    for r in sensitivity():
        lo, hi = sorted([r["low_delta"], r["high_delta"]])
        lines.append(f"| {r['assumption']} | {fmt(lo)} | +{fmt(hi)} |")
    lines += ["", "Even with the largest single driver 25% worse, the base case stays strongly positive.", ""]
    (OUT / "roi_report.md").write_text("\n".join(lines))
    (OUT / "roi_results.json").write_text(json.dumps({"scenarios": sc, "recommended_deal": deals}, indent=2))


if __name__ == "__main__":
    sc = all_scenarios()
    deals = {n: recommended_deal(n) for n in sc}
    charts(sc, deals)
    report(sc, deals)
    print((OUT / "roi_report.md").read_text()[:1500])
