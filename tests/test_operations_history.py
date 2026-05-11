from eu_ai_act.operations import compare_assessments


def test_compare_assessments_returns_expected_deltas():
    previous = {
        "run_metadata": {"run_id": "run-prev"},
        "risk_register": {
            "records": [
                {"rpn": 20, "high_risk": False},
                {"rpn": 45, "high_risk": True},
            ]
        },
        "fmea_scores": [{"rpn": 40}],
        "fairness_results": [
            {
                "metric_name": "equalized_odds_gap_by_group",
                "groups": [{"group_name": "equalized_odds_gap", "value": 0.2}],
            }
        ],
    }
    current = {
        "run_metadata": {"run_id": "run-current"},
        "risk_register": {
            "records": [
                {"rpn": 10, "high_risk": False},
                {"rpn": 20, "high_risk": False},
                {"rpn": 60, "high_risk": True},
            ]
        },
        "fmea_scores": [{"rpn": 30}],
        "fairness_results": [
            {
                "metric_name": "equalized_odds_gap_by_group",
                "groups": [{"group_name": "equalized_odds_gap", "value": 0.1}],
            }
        ],
    }

    delta = compare_assessments(current, previous)

    assert delta["previous_run_id"] == "run-prev"
    assert delta["current_run_id"] == "run-current"
    assert delta["risk_total_delta"] == 1
    assert delta["high_risk_delta"] == 0
    assert delta["avg_rpn_delta"] < 0
    assert delta["max_equalized_odds_gap_delta"] < 0
    assert delta["avg_fmea_rpn_delta"] < 0
