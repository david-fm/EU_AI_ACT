"""Framework-agnostic evaluation pipeline for compliance assessments."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from statistics import mean
import uuid
from typing import Any, Sequence

from ..adapters import BatchPrediction, DatasetAdapter, ModelAdapter
from ..adapters.utils import to_python_data
from ..compliance import ComplianceAssessment, FMEAScore, FairnessResult, RiskRecord
from ..compliance.fairness import evaluate_fairness_by_field
from ..compliance.taxonomy import resolve_stress_taxonomy
from ..compliance.stress import run_stress_testing


@dataclass(frozen=True, slots=True)
class GroupGap:
    field_name: str
    group_name: str
    positive_rate: float
    sample_count: int


@dataclass(slots=True)
class EvaluationSummary:
    framework: str
    model_name: str
    sample_count: int
    batch_count: int
    stress_domain: str | None = None
    run_id: str | None = None
    config_hash: str | None = None
    predicted_values: list[float] = field(default_factory=list)
    observed_values: list[float] = field(default_factory=list)
    group_gaps: list[GroupGap] = field(default_factory=list)
    stress_case_names: list[str] = field(default_factory=list)

    @property
    def average_prediction(self) -> float:
        return mean(self.predicted_values) if self.predicted_values else 0.0

    @property
    def average_observed(self) -> float:
        return mean(self.observed_values) if self.observed_values else 0.0


class ComplianceEvaluator:
    """Run a normalized compliance assessment over any supported model and dataset adapter."""

    def __init__(
        self,
        *,
        prediction_threshold: float = 0.5,
        batch_size: int = 32,
        stress_domain: str | None = None,
        stress_taxonomy_path: str | Path | None = None,
    ):
        self.prediction_threshold = prediction_threshold
        self.batch_size = batch_size
        self.stress_domain = stress_domain
        self.stress_taxonomy_path = stress_taxonomy_path

    def evaluate(self, model: ModelAdapter, dataset: DatasetAdapter) -> tuple[ComplianceAssessment, EvaluationSummary]:
        batches = list(dataset.iter_batches(self.batch_size))
        if not batches:
            run_id = _generate_run_id()
            config_hash = _compute_config_hash(
                {
                    "framework": model.framework,
                    "batch_size": self.batch_size,
                    "prediction_threshold": self.prediction_threshold,
                    "stress_domain": self.stress_domain,
                }
            )
            assessment = ComplianceAssessment(
                framework=model.framework,
                model_name=model.get_model_metadata().get("model_name", model.__class__.__name__),
                run_id=run_id,
                config_hash=config_hash,
            )
            assessment.risk_register.add(
                RiskRecord(
                    risk_id="R-EMPTY-DATASET",
                    title="Empty dataset",
                    description="No batches were returned by the dataset adapter.",
                    severity=5,
                    occurrence=5,
                    detectability=1,
                    strategy="inform",
                )
            )
            return assessment, EvaluationSummary(
                framework=model.framework,
                model_name=assessment.model_name,
                sample_count=0,
                batch_count=0,
                run_id=run_id,
                config_hash=config_hash,
            )

        predicted_values: list[float] = []
        observed_values: list[float] = []
        group_gaps: list[GroupGap] = []
        fairness_vectors_by_field: dict[str, dict[str, list[Any]]] = {}
        sample_count = 0
        cached_batches: list[tuple[Any, Any, Any]] = []
        model_metadata = model.get_model_metadata()
        run_id = _generate_run_id()
        config_hash = _compute_config_hash(
            {
                "framework": model.framework,
                "model_name": model_metadata.get("model_name"),
                "batch_size": self.batch_size,
                "prediction_threshold": self.prediction_threshold,
                "stress_domain": self.stress_domain,
                "metadata_fields": list(dataset.get_metadata_fields()),
            }
        )
        stress_profile = resolve_stress_taxonomy(
            self.stress_domain,
            model_metadata=model_metadata,
            metadata_fields=dataset.get_metadata_fields(),
            taxonomy_config_path=self.stress_taxonomy_path,
        )
        stress_cases = list(stress_profile.cases)

        for batch_features, batch_labels, batch_metadata in batches:
            cached_batches.append((batch_features, batch_labels, batch_metadata))
            prediction = model.predict(batch_features)
            batch_scores = _flatten_scores(prediction)

            for index, raw_score in enumerate(batch_scores):
                score = _coerce_scalar(raw_score)
                predicted_values.append(score)
                sample_count += 1

                if batch_labels is not None and index < len(batch_labels):
                    observed_values.append(_coerce_scalar(batch_labels[index]))

                if batch_metadata is not None and index < len(batch_metadata):
                    metadata = batch_metadata[index] or {}
                    true_label = None
                    if batch_labels is not None and index < len(batch_labels):
                        true_label = int(_coerce_scalar(batch_labels[index]) >= self.prediction_threshold)
                    for field_name, raw_group_value in metadata.items():
                        vectors = fairness_vectors_by_field.setdefault(
                            field_name,
                            {"group_names": [], "scores": [], "labels": []},
                        )
                        vectors["group_names"].append(str(raw_group_value))
                        vectors["scores"].append(score)
                        vectors["labels"].append(true_label)

        fairness_results = []
        for field_name, vectors in fairness_vectors_by_field.items():
            group_names = vectors["group_names"]
            y_scores = vectors["scores"]
            labels = vectors["labels"]
            y_true_binary = labels if all(label is not None for label in labels) else None

            field_results, stats, _, _ = evaluate_fairness_by_field(
                field_name=field_name,
                group_names=group_names,
                y_scores=y_scores,
                y_true_binary=y_true_binary,
                global_threshold=self.prediction_threshold,
            )
            fairness_results.extend(field_results)

            for item in stats:
                group_gaps.append(
                    GroupGap(
                        field_name=field_name,
                        group_name=item.group_name,
                        positive_rate=item.selection_rate,
                        sample_count=item.support,
                    )
                )

        stress_results = run_stress_testing(
            model,
            cached_batches,
            prediction_threshold=self.prediction_threshold,
            cases=stress_cases,
        )

        assessment = ComplianceAssessment(
            framework=model.framework,
            model_name=model_metadata.get("model_name", model.__class__.__name__),
            run_id=run_id,
            config_hash=config_hash,
            fmea_scores=_build_fmea_scores(predicted_values, observed_values),
            fairness_results=fairness_results,
            stress_results=stress_results,
        )

        for record in _build_risk_records(model, dataset, predicted_values, observed_values, group_gaps):
            assessment.risk_register.add(record)

        for record in _build_stress_risk_records(stress_results):
            assessment.risk_register.add(record)

        summary = EvaluationSummary(
            framework=model.framework,
            model_name=assessment.model_name,
            sample_count=sample_count,
            batch_count=len(batches),
            stress_domain=stress_profile.name,
            run_id=run_id,
            config_hash=config_hash,
            predicted_values=predicted_values,
            observed_values=observed_values,
            group_gaps=group_gaps,
            stress_case_names=[case.name for case in stress_cases],
        )
        return assessment, summary


def _flatten_scores(prediction: BatchPrediction) -> Sequence[Any]:
    scores = to_python_data(prediction.scores)
    if scores and isinstance(scores[0], list):
        if len(scores) == 1:
            return scores[0]
        return [row[0] if isinstance(row, list) and row else row for row in scores]
    return scores


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


def _build_fmea_scores(predicted_values: Sequence[float], observed_values: Sequence[float]) -> list[FMEAScore]:
    if not predicted_values:
        return []

    average_prediction = mean(predicted_values)
    average_observed = mean(observed_values) if observed_values else average_prediction
    prediction_gap = abs(average_prediction - average_observed)

    severity = _bucket_score(5 * (1.0 - min(1.0, prediction_gap)))
    occurrence = _bucket_score(1 + prediction_gap * 4)
    detectability = _bucket_score(3 + (1.0 - min(1.0, abs(0.5 - average_prediction) * 2)) * 2)
    rpn = severity * occurrence * detectability
    residual_rpn = max(1, int(round(rpn * 0.75)))

    return [
        FMEAScore(
            severity=severity,
            occurrence=occurrence,
            detectability=detectability,
            failure_mode="Prediction quality drift under expected operating conditions",
            root_cause="Distribution mismatch between observed and predicted outcomes",
            current_controls="Fairness analysis and stress testing enabled in evaluation pipeline",
            recommended_actions="Review thresholding strategy and retraining criteria",
            residual_rpn=residual_rpn,
            action_required=rpn >= 60,
        )
    ]


def _build_risk_records(
    model: ModelAdapter,
    dataset: DatasetAdapter,
    predicted_values: Sequence[float],
    observed_values: Sequence[float],
    group_gaps: Sequence[GroupGap],
) -> list[RiskRecord]:
    records: list[RiskRecord] = []

    if not dataset.get_metadata_fields():
        records.append(
            RiskRecord(
                risk_id="R-NO-METADATA",
                title="Missing sensitive metadata",
                description="Dataset does not expose metadata fields for fairness analysis.",
                severity=3,
                occurrence=4,
                detectability=2,
                strategy="inform",
            )
        )

    if predicted_values:
        prediction_mean = mean(predicted_values)
        observed_mean = mean(observed_values) if observed_values else prediction_mean
        prediction_gap = abs(prediction_mean - observed_mean)
        if prediction_gap >= 0.25:
            records.append(
                RiskRecord(
                    risk_id="R-PREDICTION-GAP",
                    title="Prediction and observation gap",
                    description="Model predictions diverge materially from observed labels in the evaluation set.",
                    severity=_bucket_score(5 * prediction_gap),
                    occurrence=_bucket_score(2 + prediction_gap * 4),
                    detectability=_bucket_score(3 + prediction_gap * 2),
                    strategy="mitigate",
                    cause="Prediction calibration mismatch",
                    current_controls="Batch-level quality monitoring",
                    recommended_action="Tune threshold and retraining trigger",
                )
            )

    if group_gaps:
        max_gap = _fairness_gap(group_gaps)
        if max_gap >= 0.20:
            records.append(
                RiskRecord(
                    risk_id="R-FAIRNESS-GAP",
                    title="Fairness disparity across metadata groups",
                    description="At least one metadata field shows a notable disparity across groups (selection-rate proxy).",
                    severity=_bucket_score(3 + max_gap * 10),
                    occurrence=_bucket_score(2 + max_gap * 5),
                    detectability=_bucket_score(2 + max_gap * 4),
                    strategy="mitigate",
                    cause="Subgroup imbalance or threshold mismatch",
                    current_controls="Per-group fairness metrics",
                    recommended_action="Review sampling strategy and group-specific thresholds",
                )
            )

    if not records:
        records.append(
            RiskRecord(
                risk_id="R-BASELINE",
                title="Baseline operational risk",
                description="Evaluation completed without critical issues in the current configuration.",
                severity=1,
                occurrence=1,
                detectability=5,
                strategy="inform",
                cause="Normal operating conditions",
                current_controls="Continuous compliance evaluation",
                recommended_action="Maintain periodic monitoring",
            )
        )

    return records


def _build_stress_risk_records(stress_results: Sequence[Any]) -> list[RiskRecord]:
    records: list[RiskRecord] = []
    for result in stress_results:
        performance_drop = float(getattr(result, "max_performance_drop", getattr(result, "performance_drop", 0.0)))
        entropy = float(getattr(result, "average_entropy", 0.0))
        severity = _bucket_score(1 + performance_drop * 10)
        occurrence = _bucket_score(1 + float(getattr(result, "severity", 0.0)) * 4)
        detectability = _bucket_score(2 + entropy * 3)
        if performance_drop >= 0.05 or entropy >= 0.45:
            records.append(
                RiskRecord(
                    risk_id=f"R-STRESS-{str(getattr(result, 'perturbation_name', 'UNKNOWN')).upper().replace(' ', '-')}",
                    title=f"Robustness degradation under {getattr(result, 'perturbation_name', 'stress testing')}",
                    description=(
                        f"Perturbation '{getattr(result, 'perturbation_name', 'stress testing')}' reduced "
                        f"{getattr(result, 'reference_metric', 'performance')} by {performance_drop:.3f} and "
                        f"showed average entropy {entropy:.3f}."
                    ),
                    severity=severity,
                    occurrence=occurrence,
                    detectability=detectability,
                    strategy="mitigate",
                    cause="Model sensitivity to perturbations",
                    current_controls="Stress test taxonomy by domain",
                    recommended_action="Harden training with targeted augmentation",
                )
            )

    if records:
        return records

    return [
        RiskRecord(
            risk_id="R-STRESS-BASELINE",
            title="Baseline robustness within tolerance",
            description="Stress testing completed without material degradation in the configured perturbations.",
            severity=1,
            occurrence=1,
            detectability=5,
            strategy="inform",
            cause="No material stress degradation detected",
            current_controls="Stress checks per run",
            recommended_action="Keep monitoring with latest domain taxonomy",
        )
    ]


def _fairness_gap(group_gaps: Sequence[GroupGap]) -> float:
    by_field: dict[str, list[float]] = {}
    for gap in group_gaps:
        by_field.setdefault(gap.field_name, []).append(gap.positive_rate)
    max_gap = 0.0
    for rates in by_field.values():
        if rates:
            max_gap = max(max_gap, max(rates) - min(rates))
    return max_gap


def _bucket_score(raw_value: float) -> int:
    return max(1, min(5, int(round(raw_value))))


def _generate_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def _compute_config_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]