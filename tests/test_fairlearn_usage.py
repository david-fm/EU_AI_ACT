import math

from eu_ai_act.compliance.fairness import evaluate_fairness_by_field


def _metric_map(results):
    return {item.metric_name: item for item in results}


def test_fairlearn_metrics_are_generated_with_labels():
    groups = ["A", "A", "A", "B", "B", "B"]
    y_scores = [0.9, 0.7, 0.1, 0.8, 0.2, 0.1]
    y_true = [1, 1, 0, 1, 0, 0]

    results, stats, eo_gap, di_ratio = evaluate_fairness_by_field(
        field_name="site",
        group_names=groups,
        y_scores=y_scores,
        y_true_binary=y_true,
        global_threshold=0.5,
    )

    metrics = _metric_map(results)

    assert "equalized_odds_gap_by_site" in metrics
    assert "disparate_impact_ratio_by_site" in metrics
    assert "brier_score_by_site" in metrics
    assert "ece_by_site" in metrics
    assert "optimal_threshold_by_site" in metrics
    assert "equalized_odds_gap_group_thresholded_by_site" in metrics
    assert "disparate_impact_ratio_group_thresholded_by_site" in metrics

    assert len(stats) == 2
    assert math.isfinite(eo_gap)
    assert math.isfinite(di_ratio)


def test_fairlearn_metrics_without_labels_keep_core_outputs_only():
    groups = ["A", "A", "B", "B"]
    y_scores = [0.9, 0.2, 0.7, 0.1]

    results, _stats, eo_gap, _di_ratio = evaluate_fairness_by_field(
        field_name="age_group",
        group_names=groups,
        y_scores=y_scores,
        y_true_binary=None,
        global_threshold=0.5,
    )

    metrics = _metric_map(results)

    assert "selection_rate_by_age_group" in metrics
    assert "equalized_odds_gap_by_age_group" in metrics
    assert "disparate_impact_ratio_by_age_group" in metrics

    assert "brier_score_by_age_group" not in metrics
    assert "ece_by_age_group" not in metrics
    assert "optimal_threshold_by_age_group" not in metrics
    assert eo_gap == 0.0


def test_fairlearn_stats_supports_desbalanced_groups():
    groups = ["majority"] * 8 + ["minority"] * 2
    y_scores = [0.9, 0.8, 0.7, 0.2, 0.1, 0.6, 0.55, 0.52, 0.65, 0.05]
    y_true = [1, 1, 1, 0, 0, 1, 1, 1, 1, 0]

    _results, stats, _eo_gap, _di_ratio = evaluate_fairness_by_field(
        field_name="demographic_group",
        group_names=groups,
        y_scores=y_scores,
        y_true_binary=y_true,
        global_threshold=0.5,
    )

    supports = {item.group_name: item.support for item in stats}
    assert supports["majority"] == 8
    assert supports["minority"] == 2
