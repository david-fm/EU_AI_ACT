"""Fairness evaluation primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isnan
from typing import Sequence


@dataclass(frozen=True, slots=True)
class GroupMetric:
    group_name: str
    value: float


@dataclass(slots=True)
class FairnessResult:
    metric_name: str
    groups: list[GroupMetric] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_name": self.metric_name,
            "groups": [{"group_name": group.group_name, "value": group.value} for group in self.groups],
        }


@dataclass(frozen=True, slots=True)
class GroupFairnessStats:
    group_name: str
    support: int
    selection_rate: float
    true_positive_rate: float
    false_positive_rate: float


def evaluate_fairness_by_field(
    field_name: str,
    group_names: Sequence[str],
    y_scores: Sequence[float],
    y_true_binary: Sequence[int] | None,
    *,
    global_threshold: float = 0.5,
) -> tuple[list[FairnessResult], list[GroupFairnessStats], float, float]:
    """Compute fairness metrics for a sensitive field.

    Returns fairness results, per-group stats, equalized odds gap, and disparate impact ratio.
    """

    if not group_names or len(group_names) != len(y_scores):
        return [], [], 0.0, 1.0

    from fairlearn.metrics import (
        MetricFrame,
        demographic_parity_ratio,
        equalized_odds_difference,
        false_positive_rate,
        selection_rate,
        true_positive_rate,
    )

    has_labels = y_true_binary is not None and len(y_true_binary) == len(y_scores)
    groups = list(group_names)
    y_pred = [1 if float(value) >= global_threshold else 0 for value in y_scores]
    y_true = [1 if value else 0 for value in (y_true_binary or [0] * len(y_pred))]

    selection_frame = MetricFrame(
        metrics=selection_rate,
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=groups,
    )

    if has_labels:
        tpr_frame = MetricFrame(
            metrics=true_positive_rate,
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=groups,
        )
        fpr_frame = MetricFrame(
            metrics=false_positive_rate,
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=groups,
        )
        equalized_odds_gap = float(
            equalized_odds_difference(
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=groups,
                method="between_groups",
            )
        )
    else:
        tpr_frame = None
        fpr_frame = None
        equalized_odds_gap = 0.0

    disparate_impact_ratio = float(
        demographic_parity_ratio(
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=groups,
            method="between_groups",
        )
    )

    supports = _group_supports(groups)
    group_indices = _group_indices(groups)
    stats: list[GroupFairnessStats] = []
    for group_name in supports:
        group_selection_rate = float(selection_frame.by_group[group_name])
        group_tpr = float(tpr_frame.by_group[group_name]) if tpr_frame is not None else 0.0
        group_fpr = float(fpr_frame.by_group[group_name]) if fpr_frame is not None else 0.0
        stats.append(
            GroupFairnessStats(
                group_name=group_name,
                support=supports[group_name],
                selection_rate=group_selection_rate,
                true_positive_rate=group_tpr,
                false_positive_rate=group_fpr,
            )
        )

    selection_rates = [item.selection_rate for item in stats]
    tprs = [item.true_positive_rate for item in stats]
    fprs = [item.false_positive_rate for item in stats]

    tpr_gap = _safe_gap(tprs)
    fpr_gap = _safe_gap(fprs)
    if not has_labels:
        equalized_odds_gap = 0.0

    fairness_results = [
        FairnessResult(
            metric_name=f"selection_rate_by_{field_name}",
            groups=[GroupMetric(group_name=item.group_name, value=item.selection_rate) for item in stats],
        ),
        FairnessResult(
            metric_name=f"true_positive_rate_by_{field_name}",
            groups=[GroupMetric(group_name=item.group_name, value=item.true_positive_rate) for item in stats],
        ),
        FairnessResult(
            metric_name=f"false_positive_rate_by_{field_name}",
            groups=[GroupMetric(group_name=item.group_name, value=item.false_positive_rate) for item in stats],
        ),
        FairnessResult(
            metric_name=f"equalized_odds_gap_by_{field_name}",
            groups=[
                GroupMetric(group_name="tpr_gap", value=tpr_gap),
                GroupMetric(group_name="fpr_gap", value=fpr_gap),
                GroupMetric(group_name="equalized_odds_gap", value=equalized_odds_gap),
            ],
        ),
        FairnessResult(
            metric_name=f"disparate_impact_ratio_by_{field_name}",
            groups=[GroupMetric(group_name="ratio", value=disparate_impact_ratio)],
        ),
    ]

    if has_labels:
        brier_groups = []
        ece_groups = []
        threshold_groups = []
        thresholded_scores = [0] * len(y_scores)

        for group_name, indices in group_indices.items():
            group_scores = [float(y_scores[i]) for i in indices]
            group_true = [int(y_true[i]) for i in indices]

            brier = _brier_score(group_scores, group_true)
            ece = _expected_calibration_error(group_scores, group_true)
            threshold = _optimal_threshold(group_scores, group_true)

            brier_groups.append(GroupMetric(group_name=group_name, value=brier))
            ece_groups.append(GroupMetric(group_name=group_name, value=ece))
            threshold_groups.append(GroupMetric(group_name=group_name, value=threshold))

            for idx in indices:
                thresholded_scores[idx] = 1 if float(y_scores[idx]) >= threshold else 0

        fairness_results.extend(
            [
                FairnessResult(metric_name=f"brier_score_by_{field_name}", groups=brier_groups),
                FairnessResult(metric_name=f"ece_by_{field_name}", groups=ece_groups),
                FairnessResult(metric_name=f"optimal_threshold_by_{field_name}", groups=threshold_groups),
            ]
        )

        thresholded_eo_gap = float(
            equalized_odds_difference(
                y_true=y_true,
                y_pred=thresholded_scores,
                sensitive_features=groups,
                method="between_groups",
            )
        )
        thresholded_di_ratio = float(
            demographic_parity_ratio(
                y_true=y_true,
                y_pred=thresholded_scores,
                sensitive_features=groups,
                method="between_groups",
            )
        )
        fairness_results.extend(
            [
                FairnessResult(
                    metric_name=f"equalized_odds_gap_group_thresholded_by_{field_name}",
                    groups=[GroupMetric(group_name="equalized_odds_gap", value=thresholded_eo_gap)],
                ),
                FairnessResult(
                    metric_name=f"disparate_impact_ratio_group_thresholded_by_{field_name}",
                    groups=[GroupMetric(group_name="ratio", value=thresholded_di_ratio)],
                ),
            ]
        )

    return fairness_results, stats, equalized_odds_gap, disparate_impact_ratio


def _safe_gap(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return max(values) - min(values)


def _group_supports(group_names: Sequence[str]) -> dict[str, int]:
    supports: dict[str, int] = {}
    for name in group_names:
        supports[name] = supports.get(name, 0) + 1
    return supports


def _group_indices(group_names: Sequence[str]) -> dict[str, list[int]]:
    indices: dict[str, list[int]] = {}
    for idx, name in enumerate(group_names):
        indices.setdefault(name, []).append(idx)
    return indices


def _brier_score(y_scores: Sequence[float], y_true: Sequence[int]) -> float:
    if not y_scores:
        return 0.0
    error = 0.0
    for score, true in zip(y_scores, y_true):
        diff = float(score) - float(true)
        error += diff * diff
    return error / len(y_scores)


def _expected_calibration_error(y_scores: Sequence[float], y_true: Sequence[int], bins: int = 10) -> float:
    if not y_scores:
        return 0.0

    bucket_scores: list[list[float]] = [[] for _ in range(bins)]
    bucket_true: list[list[int]] = [[] for _ in range(bins)]
    for score, true in zip(y_scores, y_true):
        value = min(max(float(score), 0.0), 1.0)
        index = min(int(value * bins), bins - 1)
        bucket_scores[index].append(value)
        bucket_true[index].append(int(true))

    total = len(y_scores)
    ece = 0.0
    for scores, labels in zip(bucket_scores, bucket_true):
        if not scores:
            continue
        conf = sum(scores) / len(scores)
        acc = sum(labels) / len(labels)
        ece += abs(conf - acc) * (len(scores) / total)
    return ece


def _optimal_threshold(y_scores: Sequence[float], y_true: Sequence[int]) -> float:
    if not y_scores:
        return 0.5

    best_threshold = 0.5
    best_score = float("-inf")
    for step in range(1, 20):
        threshold = step / 20.0
        score = _balanced_accuracy_from_threshold(y_scores, y_true, threshold)
        if isnan(score):
            continue
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold


def _balanced_accuracy_from_threshold(y_scores: Sequence[float], y_true: Sequence[int], threshold: float) -> float:
    tp = fp = tn = fn = 0
    for score, true in zip(y_scores, y_true):
        pred = 1 if float(score) >= threshold else 0
        label = int(true)
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 0:
            tn += 1
        else:
            fn += 1

    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    return 0.5 * (tpr + tnr)