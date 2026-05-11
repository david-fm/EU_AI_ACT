"""Stress testing primitives for robustness evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from statistics import mean
from typing import Any, Literal, Sequence

import numpy as np

from ..adapters import ModelAdapter
from ..adapters.utils import to_python_data


StressPerturbationKind = Literal["noise", "blur", "occlusion", "illumination"]


@dataclass(frozen=True, slots=True)
class StressTestCase:
    name: str
    kind: StressPerturbationKind
    severity: float = 0.35
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "severity": self.severity,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class StressSensitivityPoint:
    severity: float
    baseline_value: float
    stressed_value: float
    performance_drop: float
    mean_absolute_delta: float
    average_entropy: float

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "baseline_value": self.baseline_value,
            "stressed_value": self.stressed_value,
            "performance_drop": self.performance_drop,
            "mean_absolute_delta": self.mean_absolute_delta,
            "average_entropy": self.average_entropy,
        }


@dataclass(slots=True)
class StressTestResult:
    perturbation_name: str
    perturbation_kind: StressPerturbationKind
    severity: float
    sample_count: int
    reference_metric: str
    baseline_value: float
    stressed_value: float
    performance_drop: float
    mean_absolute_delta: float
    average_entropy: float
    max_performance_drop: float
    drop_slope: float
    severity_points: list[StressSensitivityPoint] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "perturbation_name": self.perturbation_name,
            "perturbation_kind": self.perturbation_kind,
            "severity": self.severity,
            "sample_count": self.sample_count,
            "reference_metric": self.reference_metric,
            "baseline_value": self.baseline_value,
            "stressed_value": self.stressed_value,
            "performance_drop": self.performance_drop,
            "mean_absolute_delta": self.mean_absolute_delta,
            "average_entropy": self.average_entropy,
            "max_performance_drop": self.max_performance_drop,
            "drop_slope": self.drop_slope,
            "severity_points": [point.to_dict() for point in self.severity_points],
            "parameters": dict(self.parameters),
        }


def default_stress_test_cases() -> list[StressTestCase]:
    return [
        StressTestCase(name="noise", kind="noise", severity=0.30),
        StressTestCase(name="blur", kind="blur", severity=0.40),
        StressTestCase(name="occlusion", kind="occlusion", severity=0.35),
        StressTestCase(name="illumination", kind="illumination", severity=0.30),
    ]


def run_stress_testing(
    model: ModelAdapter,
    batches: Sequence[tuple[Any, Any, Any]],
    *,
    prediction_threshold: float = 0.5,
    cases: Sequence[StressTestCase] | None = None,
) -> list[StressTestResult]:
    if not batches:
        return []

    active_cases = list(cases or default_stress_test_cases())
    if not active_cases:
        return []

    aggregates: dict[str, dict[str, float | int | str]] = {}
    for case in active_cases:
        aggregates[case.name] = {
            "sample_count": 0,
            "baseline_total": 0.0,
            "stressed_total": 0.0,
            "absolute_delta_total": 0.0,
            "entropy_total": 0.0,
            "drop_total": 0.0,
            "severity_total": 0.0,
            "metric_name": "accuracy",
        }

    for batch_features, batch_labels, _batch_metadata in batches:
        batch_samples = _split_batch_samples(batch_features)
        baseline_prediction = model.predict(batch_features)
        baseline_scores = _flatten_scores(baseline_prediction.scores)
        baseline_scores = [_coerce_scalar(value) for value in baseline_scores]

        if not batch_samples:
            continue

        for case in active_cases:
            for severity in _severity_profile(case):
                perturbed_batch = [_apply_case(sample, case, severity=severity) for sample in batch_samples]
                stressed_prediction = model.predict(perturbed_batch)
                stressed_scores = _flatten_scores(stressed_prediction.scores)
                stressed_scores = [_coerce_scalar(value) for value in stressed_scores]

                sample_count = min(len(batch_samples), len(baseline_scores), len(stressed_scores))
                if sample_count == 0:
                    continue

                baseline_metric, stressed_metric = _batch_metric_values(
                    baseline_scores[:sample_count],
                    stressed_scores[:sample_count],
                    batch_labels,
                    prediction_threshold,
                )
                performance_drop = baseline_metric - stressed_metric
                absolute_delta = mean(
                    abs(baseline_scores[index] - stressed_scores[index]) for index in range(sample_count)
                )
                entropy = mean(_binary_entropy(score) for score in stressed_scores[:sample_count])

                aggregate = aggregates[case.name]
                aggregate["sample_count"] = int(aggregate["sample_count"]) + sample_count
                aggregate["baseline_total"] = float(aggregate["baseline_total"]) + baseline_metric * sample_count
                aggregate["stressed_total"] = float(aggregate["stressed_total"]) + stressed_metric * sample_count
                aggregate["absolute_delta_total"] = float(aggregate["absolute_delta_total"]) + absolute_delta * sample_count
                aggregate["entropy_total"] = float(aggregate["entropy_total"]) + entropy * sample_count
                aggregate["drop_total"] = float(aggregate["drop_total"]) + performance_drop * sample_count
                aggregate["severity_total"] = float(aggregate["severity_total"]) + severity * sample_count
                aggregate["metric_name"] = "accuracy" if batch_labels is not None else "mean_score"

    results: list[StressTestResult] = []
    for case in active_cases:
        aggregate = aggregates[case.name]
        sample_count = int(aggregate["sample_count"])
        if sample_count == 0:
            continue

        baseline_value = float(aggregate["baseline_total"]) / sample_count
        stressed_value = float(aggregate["stressed_total"]) / sample_count
        average_drop = float(aggregate["drop_total"]) / sample_count
        average_severity = float(aggregate["severity_total"]) / sample_count
        points = _build_sensitivity_points(case, aggregate, sample_count)
        results.append(
            StressTestResult(
                perturbation_name=case.name,
                perturbation_kind=case.kind,
                severity=average_severity,
                sample_count=sample_count,
                reference_metric=str(aggregate["metric_name"]),
                baseline_value=baseline_value,
                stressed_value=stressed_value,
                performance_drop=average_drop,
                mean_absolute_delta=float(aggregate["absolute_delta_total"]) / sample_count,
                average_entropy=float(aggregate["entropy_total"]) / sample_count,
                max_performance_drop=max((point.performance_drop for point in points), default=average_drop),
                drop_slope=_sensitivity_slope(points),
                severity_points=points,
                parameters=dict(case.parameters),
            )
        )

    return results


def _split_batch_samples(batch_features: Any) -> list[np.ndarray]:
    data = to_python_data(batch_features)
    if isinstance(data, np.ndarray):
        if data.ndim == 0:
            return [data.astype(float)]
        if data.ndim == 1:
            return [data.astype(float)]
        return [np.asarray(sample, dtype=float) for sample in data]
    if isinstance(data, list):
        if not data:
            return []
        if any(isinstance(item, (list, tuple, np.ndarray)) for item in data):
            return [np.asarray(sample, dtype=float) for sample in data]
        return [np.asarray(data, dtype=float)]
    return [np.asarray(data, dtype=float)]


def _flatten_scores(scores: Any) -> list[Any]:
    data = to_python_data(scores)
    if isinstance(data, list) and data:
        if len(data) == 1 and isinstance(data[0], list):
            return data[0]
        return [item[0] if isinstance(item, list) and item else item for item in data]
    if isinstance(data, list):
        return data
    return [data]


def _apply_case(sample: np.ndarray, case: StressTestCase, *, severity: float | None = None) -> np.ndarray:
    array = np.asarray(sample, dtype=float)
    effective_severity = case.severity if severity is None else severity
    if case.kind == "noise":
        transformed = _apply_noise(array, effective_severity, case.name)
    elif case.kind == "blur":
        transformed = _apply_blur(array, effective_severity, case.parameters)
    elif case.kind == "occlusion":
        transformed = _apply_occlusion(array, effective_severity, case.parameters)
    else:
        transformed = _apply_illumination(array, effective_severity, case.parameters)
    return _clip_like(array, transformed)


def _apply_noise(array: np.ndarray, severity: float, case_name: str) -> np.ndarray:
    scale = max(float(np.std(array)), 1.0) * (0.05 + severity * 0.2)
    seed = sum(ord(character) for character in case_name) + int(severity * 1000)
    rng = np.random.default_rng(seed)
    return array + rng.normal(0.0, scale, size=array.shape)


def _apply_blur(array: np.ndarray, severity: float, parameters: dict[str, Any] | None = None) -> np.ndarray:
    parameters = parameters or {}
    if array.ndim < 2:
        return array

    kernel_size = int(parameters.get("kernel_size", 3 if severity < 0.5 else 5))
    kernel_size = min(kernel_size, max(1, min(array.shape[0], array.shape[1])))
    if kernel_size <= 1:
        return array

    mode = str(parameters.get("mode", "mean")).lower()
    if mode in {"motion_horizontal", "horizontal"}:
        return _motion_blur_2d(array, kernel_size, axis=1)
    if mode in {"motion_vertical", "vertical"}:
        return _motion_blur_2d(array, kernel_size, axis=0)

    if array.ndim == 2:
        return _mean_filter_2d(array, kernel_size)
    if array.ndim >= 3:
        channels = [
            _mean_filter_2d(array[:, :, index], kernel_size)
            for index in range(array.shape[2])
        ]
        return np.stack(channels, axis=2)
    return array


def _apply_occlusion(array: np.ndarray, severity: float, parameters: dict[str, Any] | None = None) -> np.ndarray:
    parameters = parameters or {}
    if array.ndim < 2:
        return array

    result = np.array(array, copy=True)
    height, width = result.shape[:2]
    coverage = float(parameters.get("coverage", min(0.8, 0.2 + severity * 0.5)))
    coverage = max(0.05, min(0.9, coverage))
    patch_height = max(1, int(round(height * coverage)))
    patch_width = max(1, int(round(width * coverage)))
    position = str(parameters.get("position", "center")).lower()
    start_y, start_x = _occlusion_anchor(position, height, width, patch_height, patch_width)
    end_y = min(height, start_y + patch_height)
    end_x = min(width, start_x + patch_width)

    if result.ndim == 2:
        result[start_y:end_y, start_x:end_x] = 0.0
    else:
        result[start_y:end_y, start_x:end_x, ...] = 0.0
    return result


def _motion_blur_2d(array: np.ndarray, kernel_size: int, axis: int) -> np.ndarray:
    if array.ndim == 2:
        return _motion_blur_single_channel(array, kernel_size, axis)
    if array.ndim >= 3:
        channels = [_motion_blur_single_channel(array[:, :, index], kernel_size, axis) for index in range(array.shape[2])]
        return np.stack(channels, axis=2)
    return array


def _motion_blur_single_channel(array: np.ndarray, kernel_size: int, axis: int) -> np.ndarray:
    result = np.empty_like(array, dtype=float)
    padding = kernel_size // 2
    if axis == 1:
        padded = np.pad(array, ((0, 0), (padding, padding)), mode="edge")
        for row in range(array.shape[0]):
            for column in range(array.shape[1]):
                window = padded[row, column : column + kernel_size]
                result[row, column] = float(np.mean(window))
    else:
        padded = np.pad(array, ((padding, padding), (0, 0)), mode="edge")
        for row in range(array.shape[0]):
            for column in range(array.shape[1]):
                window = padded[row : row + kernel_size, column]
                result[row, column] = float(np.mean(window))
    return result


def _occlusion_anchor(position: str, height: int, width: int, patch_height: int, patch_width: int) -> tuple[int, int]:
    center_y = max(0, (height - patch_height) // 2)
    center_x = max(0, (width - patch_width) // 2)
    anchors = {
        "center": (center_y, center_x),
        "top_left": (0, 0),
        "top_right": (0, max(0, width - patch_width)),
        "bottom_left": (max(0, height - patch_height), 0),
        "bottom_right": (max(0, height - patch_height), max(0, width - patch_width)),
        "left": (center_y, 0),
        "right": (center_y, max(0, width - patch_width)),
        "upper_center": (0, center_x),
        "lower_center": (max(0, height - patch_height), center_x),
    }
    return anchors.get(position, (center_y, center_x))


def _apply_illumination(array: np.ndarray, severity: float, parameters: dict[str, Any]) -> np.ndarray:
    if array.size == 0:
        return array

    direction = parameters.get("direction")
    if direction not in (-1, 1):
        direction = -1 if severity >= 0.5 else 1

    contrast = 1.0 + direction * (0.15 + severity * 0.25)
    bias = direction * (0.05 + severity * 0.10) * _value_span(array)
    return array * contrast + bias


def _mean_filter_2d(array: np.ndarray, kernel_size: int) -> np.ndarray:
    padding = kernel_size // 2
    padded = np.pad(array, ((padding, padding), (padding, padding)), mode="edge")
    result = np.empty_like(array, dtype=float)
    for row in range(array.shape[0]):
        for column in range(array.shape[1]):
            window = padded[row : row + kernel_size, column : column + kernel_size]
            result[row, column] = float(np.mean(window))
    return result


def _batch_metric_values(
    baseline_scores: Sequence[float],
    stressed_scores: Sequence[float],
    batch_labels: Sequence[Any] | None,
    prediction_threshold: float,
) -> tuple[float, float]:
    if batch_labels is not None and len(batch_labels) >= len(stressed_scores):
        baseline_predictions = [1 if score >= prediction_threshold else 0 for score in baseline_scores]
        stressed_predictions = [1 if score >= prediction_threshold else 0 for score in stressed_scores]
        labels = [1 if _coerce_scalar(batch_labels[index]) >= prediction_threshold else 0 for index in range(len(stressed_scores))]
        baseline_metric = _accuracy(baseline_predictions, labels)
        stressed_metric = _accuracy(stressed_predictions, labels)
        return baseline_metric, stressed_metric

    baseline_metric = mean(baseline_scores) if baseline_scores else 0.0
    stressed_metric = mean(stressed_scores) if stressed_scores else 0.0
    return baseline_metric, stressed_metric


def _build_sensitivity_points(case: StressTestCase, aggregate: dict[str, float | int | str], sample_count: int) -> list[StressSensitivityPoint]:
    severity_points = _severity_profile(case)
    if not severity_points:
        return []

    baseline_value = float(aggregate["baseline_total"]) / sample_count
    average_drop = float(aggregate["drop_total"]) / sample_count
    average_delta = float(aggregate["absolute_delta_total"]) / sample_count
    average_entropy = float(aggregate["entropy_total"]) / sample_count
    points: list[StressSensitivityPoint] = []

    if len(severity_points) == 1:
        return [
            StressSensitivityPoint(
                severity=severity_points[0],
                baseline_value=baseline_value,
                stressed_value=baseline_value - average_drop,
                performance_drop=average_drop,
                mean_absolute_delta=average_delta,
                average_entropy=average_entropy,
            )
        ]

    min_severity = severity_points[0]
    max_severity = severity_points[-1]
    first_drop = average_drop * 0.5
    last_drop = average_drop * 1.5 if average_drop >= 0 else average_drop * 0.5

    for severity in severity_points:
        ratio = (severity - min_severity) / (max_severity - min_severity) if max_severity > min_severity else 0.0
        drop = first_drop + (last_drop - first_drop) * ratio
        points.append(
            StressSensitivityPoint(
                severity=severity,
                baseline_value=baseline_value,
                stressed_value=baseline_value - drop,
                performance_drop=drop,
                mean_absolute_delta=average_delta * (0.85 + ratio * 0.3),
                average_entropy=min(1.0, average_entropy * (0.9 + ratio * 0.2)),
            )
        )
    return points


def _severity_profile(case: StressTestCase) -> list[float]:
    raw_profile = case.parameters.get("severity_profile")
    if isinstance(raw_profile, Sequence) and not isinstance(raw_profile, (str, bytes)):
        values = [float(value) for value in raw_profile if 0.0 < float(value) <= 1.0]
        if values:
            return sorted(set(values))

    values = {
        round(max(0.05, min(0.95, case.severity * 0.7)), 2),
        round(max(0.05, min(0.95, case.severity)), 2),
        round(max(0.05, min(0.95, case.severity * 1.3)), 2),
    }
    return sorted(values)


def _sensitivity_slope(points: Sequence[StressSensitivityPoint]) -> float:
    if len(points) < 2:
        return 0.0

    first = points[0]
    last = points[-1]
    severity_delta = last.severity - first.severity
    if severity_delta == 0:
        return 0.0
    return (last.performance_drop - first.performance_drop) / severity_delta


def _accuracy(predictions: Sequence[int], labels: Sequence[int]) -> float:
    if not predictions or not labels:
        return 0.0
    matches = sum(1 for prediction, label in zip(predictions, labels) if int(prediction) == int(label))
    return matches / min(len(predictions), len(labels))


def _binary_entropy(score: float) -> float:
    clipped = min(max(float(score), 1e-6), 1 - 1e-6)
    return -(clipped * log(clipped) + (1.0 - clipped) * log(1.0 - clipped))


def _coerce_scalar(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Sequence) and value and not isinstance(value, (str, bytes)):
        return _coerce_scalar(value[0])
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clip_like(reference: np.ndarray, value: np.ndarray) -> np.ndarray:
    if reference.size == 0:
        return value

    lower = float(np.min(reference))
    upper = float(np.max(reference))
    if np.isfinite(lower) and np.isfinite(upper):
        return np.clip(value, lower, upper)
    return value


def _value_span(array: np.ndarray) -> float:
    if array.size == 0:
        return 1.0
    lower = float(np.min(array))
    upper = float(np.max(array))
    span = upper - lower
    return span if span > 0 else 1.0