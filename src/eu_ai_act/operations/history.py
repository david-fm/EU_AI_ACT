"""Run history helpers for versioned assessments and comparisons."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def load_assessment_json(path: str | Path) -> dict[str, Any]:
    """Load an assessment JSON file as a dictionary."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_assessments(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Build a compact delta summary between two assessment payloads."""

    current_risks = current.get("risk_register", {}).get("records", [])
    previous_risks = previous.get("risk_register", {}).get("records", [])

    current_total = len(current_risks)
    previous_total = len(previous_risks)

    current_high = sum(1 for item in current_risks if item.get("high_risk"))
    previous_high = sum(1 for item in previous_risks if item.get("high_risk"))

    current_avg_rpn = mean([int(item.get("rpn", 0)) for item in current_risks]) if current_risks else 0.0
    previous_avg_rpn = mean([int(item.get("rpn", 0)) for item in previous_risks]) if previous_risks else 0.0

    current_eo_gap = _max_equalized_odds_gap(current)
    previous_eo_gap = _max_equalized_odds_gap(previous)

    current_fmea = current.get("fmea_scores", [])
    previous_fmea = previous.get("fmea_scores", [])
    current_avg_fmea_rpn = mean([int(item.get("rpn", 0)) for item in current_fmea]) if current_fmea else 0.0
    previous_avg_fmea_rpn = mean([int(item.get("rpn", 0)) for item in previous_fmea]) if previous_fmea else 0.0

    return {
        "previous_run_id": previous.get("run_metadata", {}).get("run_id"),
        "current_run_id": current.get("run_metadata", {}).get("run_id"),
        "risk_total_delta": current_total - previous_total,
        "high_risk_delta": current_high - previous_high,
        "avg_rpn_delta": round(current_avg_rpn - previous_avg_rpn, 4),
        "max_equalized_odds_gap_delta": round(current_eo_gap - previous_eo_gap, 4),
        "avg_fmea_rpn_delta": round(current_avg_fmea_rpn - previous_avg_fmea_rpn, 4),
    }


def _max_equalized_odds_gap(report: dict[str, Any]) -> float:
    fairness_results = report.get("fairness_results", [])
    max_gap = 0.0
    for metric in fairness_results:
        metric_name = str(metric.get("metric_name", ""))
        if "equalized_odds_gap_by_" not in metric_name:
            continue
        for group in metric.get("groups", []):
            if group.get("group_name") == "equalized_odds_gap":
                value = float(group.get("value", 0.0))
                max_gap = max(max_gap, value)
    return max_gap
