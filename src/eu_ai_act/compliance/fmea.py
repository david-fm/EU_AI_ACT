"""FMEA scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FMEAScore:
    severity: int
    occurrence: int
    detectability: int
    failure_mode: str | None = None
    root_cause: str | None = None
    current_controls: str | None = None
    recommended_actions: str | None = None
    residual_rpn: int | None = None
    action_required: bool = False

    @property
    def rpn(self) -> int:
        return self.severity * self.occurrence * self.detectability

    @property
    def high_risk(self) -> bool:
        return self.rpn >= 100

    def to_dict(self) -> dict[str, int]:
        return {
            "severity": self.severity,
            "occurrence": self.occurrence,
            "detectability": self.detectability,
            "rpn": self.rpn,
            "failure_mode": self.failure_mode,
            "root_cause": self.root_cause,
            "current_controls": self.current_controls,
            "recommended_actions": self.recommended_actions,
            "residual_rpn": self.residual_rpn,
            "high_risk": self.high_risk,
            "action_required": self.action_required,
        }