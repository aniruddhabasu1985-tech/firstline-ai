from roi.model import all_scenarios, recommended_deal, ai_cost_per_case


def test_tiered_routing_cheaper_than_frontier_everywhere():
    assert ai_cost_per_case() < ai_cost_per_case(strategy="all_frontier") / 2


def test_scenarios_are_ordered():
    s = all_scenarios()
    assert s["conservative"]["client_net_benefit_monthly"] < s["base"]["client_net_benefit_monthly"] < s["optimistic"]["client_net_benefit_monthly"]


def test_capacity_not_double_counted():
    s = all_scenarios()["base"]
    assert s["net_freed_l1_fte"] < s["fte_model"]["freed_fte_equivalent"]


def test_recommended_deal_pays_back_for_both_parties_in_base():
    d = recommended_deal("base")
    for model in ("fte_billing", "per_case_billing"):
        assert d[model]["client_payback_months"] is not None and d[model]["client_payback_months"] < 12
        assert d[model]["provider_payback_months"] is not None and d[model]["provider_payback_months"] < 12
