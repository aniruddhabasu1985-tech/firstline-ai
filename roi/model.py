"""
ROI model — two commercial structures, two beneficiaries, three scenarios.

Design principles (see docs/09-roi.md for the full walkthrough):
  - Every number traces to one assumption in roi/assumptions.json.
  - Benefits are split into CASH (money that stops being spent) and
    CAPACITY (hours freed). Capacity is only counted at a stated
    realization rate, because freed hours are not savings until used.
  - Retention upside is OFF by default. It's real, but it's the easiest
    number to challenge, so the base case is built without it.
  - Both parties are modeled. A proposal that only works for one side of
    an outsourcing relationship doesn't get signed.
"""

from __future__ import annotations
import json
from pathlib import Path
from firstline.config import TASK_ROUTING, MODELS, token_cost

A = json.loads((Path(__file__).parent / "assumptions.json").read_text())


def ai_cost_per_case(a=A, strategy: str = "tiered") -> float:
    """strategy='tiered' uses config routing; 'all_frontier' prices every call on the reasoning tier (the 'tank')."""
    total = 0.0
    for t in a["token_budget_per_case"]:
        if strategy == "all_frontier" and t["task"] != "embed":
            model = "claude-sonnet-5"
        else:
            model = TASK_ROUTING[t["task"]][0]
        total += t["calls"] * token_cost(model, t["in"], t["out"])
    return total * (1 + a["ai_cost_buffer_pct"] / 100)


def scenario(name: str, a=A) -> dict:
    s = a["scenarios"][name]
    team, bill, vol, base, core, impl = a["team"], a["billing"], a["volume"], a["baseline"], a["core_team"], a["implementation"]
    l1_cases = team["l1_engineers"] * vol["cases_per_l1_fte_month"]
    billed_fte = team["l1_engineers"] + team["licensing_fte"] + team["knowledge_fte"]
    rate, pcost = bill["rate_per_fte_month"], bill["provider_delivery_cost_per_fte_month"]

    core_cost_per_case = core["loaded_cost_per_engineer_month"] / core["elevated_cases_per_engineer_month"]
    core_hourly = core["loaded_cost_per_engineer_month"] / core["hours_per_month"]

    # --- Benefit levers (monthly) ------------------------------------------
    elevations_avoided = l1_cases * (base["elevation_pct"] - s["elevation_to_pct"]) / 100
    lever_elevation = elevations_avoided * core_cost_per_case

    swarms_base = l1_cases * base["swarms_per_100_cases"] / 100
    swarm_hours_base = swarms_base * base["core_hours_per_swarm"]
    swarm_hours_after = swarms_base * (1 - s["swarm_volume_reduction_pct"] / 100) * base["core_hours_per_swarm"] * (1 - s["swarm_time_reduction_pct"] / 100)
    lever_swarm = (swarm_hours_base - swarm_hours_after) * core_hourly

    freed_fte = team["l1_engineers"] * s["productivity_gain_pct"] / 100
    cases_per_fte_after = vol["cases_per_l1_fte_month"] * (1 + s["productivity_gain_pct"] / 100)
    # Net out the capacity L1 spends absorbing work that used to be elevated to Core
    # (otherwise the same benefit is counted twice: once as Core cost avoided, once as free L1 time).
    absorbed_fte = elevations_avoided / cases_per_fte_after
    net_freed_fte = max(0.0, freed_fte - absorbed_fte)
    lever_capacity = net_freed_fte * rate * s["capacity_realization_pct"] / 100

    lever_scripts = s["script_incidents_avoided_per_year"] * a["cost_per_script_incident_usd"] / 12

    ru = a["retention_upside"]
    lever_retention = (ru["supported_arr_usd"] * ru["churn_reduction_pct_points"] / 100 / 12) if ru["enabled"] else 0.0

    ai_case = ai_cost_per_case(a)
    run_cost = l1_cases * ai_case + impl["platform_run_usd_month"] + impl["maintenance_usd_month"]
    one_time = impl["one_time_build_usd"] + impl["security_review_and_pentest_usd"]

    client_gross = lever_elevation + lever_swarm + lever_capacity + lever_scripts + lever_retention
    client_net_month = client_gross - run_cost
    payback_months = one_time / client_net_month if client_net_month > 0 else None

    # --- Commercial model A: FTE billing ------------------------------------
    provider_rev_fte = billed_fte * rate
    provider_margin_fte = billed_fte * (rate - pcost)
    # Risk to provider if client converts ALL freed capacity into headcount cuts:
    rev_at_risk = net_freed_fte * rate
    # Recommended structure: hold headcount; freed L1 capacity absorbs the elevated-
    # tier work pulled back from Core + volume growth; provider bills an AI
    # enablement fee equal to run cost + margin.
    enablement_fee = round(run_cost * 1.25, 0)
    share = impl.get("provider_share_of_one_time_pct", 50) / 100
    provider_one_time = one_time * share
    client_one_time = one_time - provider_one_time
    client_net_fte = client_gross - enablement_fee               # client pays the fee instead of raw run cost
    provider_gain_fte = enablement_fee - run_cost                  # fee margin; headcount held
    provider_gain_case = None  # filled below

    # --- Commercial model B: per-case billing -------------------------------
    price_parity = rate / vol["cases_per_l1_fte_month"]
    unit_cost_before = pcost / vol["cases_per_l1_fte_month"]
    unit_cost_after = pcost / cases_per_fte_after + ai_case
    unit_saving = unit_cost_before - unit_cost_after
    price_after = price_parity - unit_saving * a["per_case_model"]["gainshare_to_client_pct"] / 100
    l1_cases_after = l1_cases + elevations_avoided          # work pulled back from Core is now billable at L1
    provider_margin_case_before = l1_cases * (price_parity - unit_cost_before)
    provider_margin_case_after = l1_cases_after * (price_after - unit_cost_after)
    client_l1_bill_before = l1_cases * price_parity
    client_l1_bill_after = l1_cases_after * price_after
    client_total_before = client_l1_bill_before + (l1_cases * base["elevation_pct"] / 100) * core_cost_per_case + swarm_hours_base * core_hourly
    client_total_after = client_l1_bill_after + (l1_cases * s["elevation_to_pct"] / 100) * core_cost_per_case + swarm_hours_after * core_hourly

    provider_gain_case = provider_margin_case_after - provider_margin_case_before
    client_gain_case = client_total_before - client_total_after
    pb = lambda cost, gain: round(cost / gain, 1) if gain > 0 else None
    r = lambda x: round(x, 2)
    return {
        "scenario": name,
        "l1_cases_per_month": l1_cases,
        "ai_cost_per_case_usd": round(ai_case, 4),
        "net_freed_l1_fte": r(net_freed_fte),
        "levers_monthly": {"elevation_cost_avoided": r(lever_elevation), "core_swarm_time_saved": r(lever_swarm),
                           "l1_capacity_value_realized": r(lever_capacity), "script_incidents_avoided": r(lever_scripts),
                           "retention_upside": r(lever_retention)},
        "run_cost_monthly": r(run_cost), "one_time_cost": one_time,
        "client_net_benefit_monthly": r(client_net_month),
        "client_net_benefit_annual": r(client_net_month * 12),
        "payback_months": r(payback_months) if payback_months else None,
        "roi_year1_pct": r(100 * (client_net_month * 12 - one_time) / one_time),
        "three_year_net_usd": r(client_net_month * 36 - one_time),
        "fte_model": {"provider_monthly_revenue": provider_rev_fte, "provider_monthly_margin": provider_margin_fte,
                      "freed_fte_equivalent": r(freed_fte), "provider_revenue_at_risk_if_cut": r(rev_at_risk),
                      "recommended_ai_enablement_fee_monthly": enablement_fee,
                      "client_net_monthly_with_fee": r(client_net_fte),
                      "client_payback_months_on_share": pb(client_one_time, client_net_fte),
                      "provider_monthly_gain_headcount_held": r(provider_gain_fte),
                      "provider_payback_months_on_share": pb(provider_one_time, provider_gain_fte)},
        "per_case_model": {"parity_price_per_case": r(price_parity), "unit_cost_before": r(unit_cost_before),
                           "unit_cost_after": r(unit_cost_after), "price_after_gainshare": r(price_after),
                           "provider_margin_monthly_before": r(provider_margin_case_before),
                           "provider_margin_monthly_after": r(provider_margin_case_after),
                           "client_total_support_cost_before": r(client_total_before),
                           "client_total_support_cost_after": r(client_total_after),
                           "client_monthly_saving": r(client_gain_case),
                           "provider_monthly_margin_gain": r(provider_gain_case),
                           "client_payback_months_on_share": pb(client_one_time, client_gain_case - run_cost * 0),
                           "provider_payback_months_on_share": pb(provider_one_time, provider_gain_case - run_cost)},
    }


def recommended_deal(name: str, a=A) -> dict:
    """Value-sharing terms so BOTH parties pay back. Only verifiable cash levers
    (Core elevation cost, Core swarm time, script incidents) are shared;
    capacity value is not, because it isn't cash until someone spends it."""
    base = scenario(name, a)
    d = a["recommended_deal"]
    L = base["levers_monthly"]
    verified_cash = L["elevation_cost_avoided"] + L["core_swarm_time_saved"] + L["script_incidents_avoided"]
    gross = sum(L.values())
    run = base["run_cost_monthly"]
    one_time = base["one_time_cost"]
    p_share = a["implementation"]["provider_share_of_one_time_pct"] / 100
    p_one, c_one = one_time * p_share, one_time * (1 - p_share)
    fee = base["fte_model"]["recommended_ai_enablement_fee_monthly"]

    # FTE billing: headcount held, enablement fee, outcome share of verified cash savings
    outcome_fte = verified_cash * d["fte_outcome_share_pct"] / 100
    fte_client = gross - fee - outcome_fte
    fte_provider = (fee - run) + outcome_fte

    # Per-case billing: smaller price gainshare, outcome share on Core savings, run cost split
    pc = base["per_case_model"]
    unit_saving = pc["unit_cost_before"] - pc["unit_cost_after"]
    cases_after = base["l1_cases_per_month"] * (1 + 0)  # base volume
    price = pc["parity_price_per_case"] - unit_saving * d["per_case_gainshare_to_client_pct"] / 100
    elev_absorbed = base["levers_monthly"]["elevation_cost_avoided"] / (a["core_team"]["loaded_cost_per_engineer_month"] / a["core_team"]["elevated_cases_per_engineer_month"])
    billed_cases = cases_after + elev_absorbed
    prov_margin_gain = billed_cases * (price - pc["unit_cost_after"]) - cases_after * (pc["parity_price_per_case"] - pc["unit_cost_before"])
    core_saving = L["elevation_cost_avoided"] + L["core_swarm_time_saved"]
    outcome_case = core_saving * d["per_case_outcome_share_pct"] / 100
    client_run = run * d["per_case_client_funds_run_cost_pct"] / 100
    case_provider = prov_margin_gain + outcome_case - (run - client_run)
    client_bill_delta = billed_cases * price - cases_after * pc["parity_price_per_case"]
    case_client = core_saving + L["script_incidents_avoided"] - client_bill_delta - outcome_case - client_run

    pb = lambda cost, g: round(cost / g, 1) if g > 0 else None
    r = lambda x: round(x, 2)
    return {"scenario": name, "one_time_split": {"client": c_one, "provider": p_one},
            "fte_billing": {"client_net_monthly": r(fte_client), "provider_net_monthly": r(fte_provider),
                            "client_payback_months": pb(c_one, fte_client), "provider_payback_months": pb(p_one, fte_provider),
                            "client_share_of_value_pct": r(100 * fte_client / (fte_client + fte_provider))},
            "per_case_billing": {"price_per_case": r(price), "client_net_monthly": r(case_client),
                                 "provider_net_monthly": r(case_provider),
                                 "client_payback_months": pb(c_one, case_client), "provider_payback_months": pb(p_one, case_provider),
                                 "client_share_of_value_pct": r(100 * case_client / (case_client + case_provider)) if case_client + case_provider > 0 else None}}


def all_scenarios(a=A) -> dict:
    return {n: scenario(n, a) for n in a["scenarios"]}


def sensitivity(swing_pct: float = 25, a=A) -> list[dict]:
    """Moves one assumption at a time by +/- swing_pct and reports the change
    in base-case client net monthly benefit. Answers: 'what if we're wrong about X?'"""
    import copy
    base = scenario("base", a)["client_net_benefit_monthly"]
    knobs = [
        ("Core loaded cost / engineer", ("core_team", "loaded_cost_per_engineer_month")),
        ("Elevation reduction achieved", ("scenarios", "base", "elevation_to_pct")),
        ("L1 productivity gain", ("scenarios", "base", "productivity_gain_pct")),
        ("Capacity realization", ("scenarios", "base", "capacity_realization_pct")),
        ("Swarm volume reduction", ("scenarios", "base", "swarm_volume_reduction_pct")),
        ("Script incidents avoided / yr", ("scenarios", "base", "script_incidents_avoided_per_year")),
        ("Platform + maintenance run cost", ("implementation", "platform_run_usd_month")),
    ]
    out = []
    for label, path in knobs:
        vals = []
        for sign in (-1, 1):
            b = copy.deepcopy(a)
            node = b
            for k in path[:-1]:
                node = node[k]
            if path[-1] == "elevation_to_pct":
                gap = a["baseline"]["elevation_pct"] - node[path[-1]]
                node[path[-1]] = a["baseline"]["elevation_pct"] - gap * (1 + sign * swing_pct / 100)
            else:
                node[path[-1]] = node[path[-1]] * (1 + sign * swing_pct / 100)
            vals.append(scenario("base", b)["client_net_benefit_monthly"] - base)
        out.append({"assumption": label, "low_delta": round(vals[0], 0), "high_delta": round(vals[1], 0),
                    "range": round(abs(vals[1] - vals[0]), 0)})
    return sorted(out, key=lambda r: -r["range"])
