"""Top-level compliance assessment aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .fairness import FairnessResult
from .fmea import FMEAScore
from .stress import StressTestResult
from .risk import RiskRegister


@dataclass(slots=True)
class ComplianceAssessment:
    framework: str
    model_name: str
    run_id: str | None = None
    config_hash: str | None = None
    run_timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risk_register: RiskRegister = field(default_factory=RiskRegister)
    fmea_scores: list[FMEAScore] = field(default_factory=list)
    fairness_results: list[FairnessResult] = field(default_factory=list)
    stress_results: list[StressTestResult] = field(default_factory=list)
    comparison_to_previous_run: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "framework": self.framework,
            "model_name": self.model_name,
            "run_metadata": {
                "run_id": self.run_id,
                "config_hash": self.config_hash,
                "run_timestamp_utc": self.run_timestamp_utc,
            },
            "risk_register": self.risk_register.to_dict(),
            "fmea_scores": [score.to_dict() for score in self.fmea_scores],
            "fairness_results": [result.to_dict() for result in self.fairness_results],
            "stress_results": [result.to_dict() for result in self.stress_results],
            "comparison_to_previous_run": self.comparison_to_previous_run,
        }