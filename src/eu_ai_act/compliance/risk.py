"""Risk register primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import tomllib
from pathlib import Path


RiskStrategy = Literal["eliminate", "mitigate", "inform"]
MitigationStatus = Literal["pending", "applied", "verified"]


@dataclass(slots=True)
class RiskRecord:
    risk_id: str
    title: str
    description: str
    severity: int
    occurrence: int
    detectability: int
    strategy: RiskStrategy
    cause: str | None = None
    current_controls: str | None = None
    recommended_action: str | None = None
    residual_rpn: int | None = None
    mitigation_status: MitigationStatus = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def rpn(self) -> int:
        return self.severity * self.occurrence * self.detectability

    @property
    def high_risk(self) -> bool:
        return self.rpn >= 40

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["rpn"] = self.rpn
        payload["high_risk"] = self.high_risk
        return payload


@dataclass(slots=True)
class RiskRegister:
    records: list[RiskRecord] = field(default_factory=list)

    def add(self, record: RiskRecord) -> None:
        self.records.append(record)

    def to_dict(self) -> dict[str, object]:
        return {
            "records": [record.to_dict() for record in self.records],
            "total_records": len(self.records),
        }


class RiskConfig:
    """Configuration loader for risk enrichment."""

    def __init__(self, config_path: Path | None = None, domain: str | None = None):
        self.config_path = config_path or Path("config/risk.toml")
        self.domain = domain
        self._config: dict[str, Any] = {}
        self._domain_config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                self._config = tomllib.load(f)

        if self.domain:
            domain_path = Path(f"config/domains/{self.domain}.toml")
            if domain_path.exists():
                with open(domain_path, "rb") as f:
                    self._domain_config = tomllib.load(f)

    def get_rpn_thresholds(self) -> dict[str, int]:
        """Get RPN thresholds from configuration."""
        fmea_config = self._config.get("fmea", {})
        return {
            "high": fmea_config.get("high_rpn_threshold", 120),
            "medium": fmea_config.get("medium_rpn_threshold", 60),
            "low": fmea_config.get("low_rpn_threshold", 20),
        }

    def get_residual_targets(self) -> dict[str, int]:
        """Get residual RPN targets from configuration."""
        fmea_config = self._config.get("fmea", {})
        return {
            "high": fmea_config.get("residual_rpn_target_high", 80),
            "medium": fmea_config.get("residual_rpn_target_medium", 40),
            "low": fmea_config.get("residual_rpn_target_low", 10),
        }


class RiskEnricher:
    """Enriches risk records with configurable thresholds and residual risk."""

    def __init__(self, config: RiskConfig):
        self.config = config
        self.thresholds = config.get_rpn_thresholds()
        self.residual_targets = config.get_residual_targets()

    def enrich_record(self, record: RiskRecord) -> RiskRecord:
        """Enrich a single risk record."""
        rpn = record.rpn
        mitigation_status = self._determine_mitigation_status(record)
        residual_rpn = self._calculate_residual_rpn(record)

        return RiskRecord(
            risk_id=record.risk_id,
            title=record.title,
            description=record.description,
            severity=record.severity,
            occurrence=record.occurrence,
            detectability=record.detectability,
            strategy=record.strategy,
            cause=record.cause,
            current_controls=record.current_controls,
            recommended_action=record.recommended_action,
            residual_rpn=residual_rpn,
            mitigation_status=mitigation_status,
            created_at=record.created_at,
        )

    def _determine_mitigation_status(self, record: RiskRecord) -> MitigationStatus:
        """Determine mitigation status based on controls and actions."""
        if record.current_controls and record.recommended_action:
            return "applied"
        elif record.current_controls:
            return "pending"
        else:
            return "pending"

    def _calculate_residual_rpn(self, record: RiskRecord) -> int | None:
        """Calculate residual RPN based on mitigation effectiveness."""
        if not record.current_controls:
            return None

        # Estimate reduction based on controls effectiveness
        reduction_factor = self._estimate_reduction_factor(record)
        residual_rpn = int(record.rpn * (1 - reduction_factor))

        # Ensure residual doesn't go below target
        target = self._get_residual_target(record.rpn)
        return max(residual_rpn, target)

    def _estimate_reduction_factor(self, record: RiskRecord) -> float:
        """Estimate risk reduction factor based on controls."""
        if not record.current_controls:
            return 0.0

        controls_lower = record.current_controls.lower()

        # Higher reduction for more comprehensive controls
        if "dual" in controls_lower or "multiple" in controls_lower:
            return 0.4
        elif "automated" in controls_lower or "threshold" in controls_lower:
            return 0.3
        elif "monitoring" in controls_lower or "review" in controls_lower:
            return 0.2
        else:
            return 0.1

    def _get_residual_target(self, rpn: int) -> int:
        """Get residual RPN target based on initial RPN."""
        if rpn >= self.thresholds["high"]:
            return self.residual_targets["high"]
        elif rpn >= self.thresholds["medium"]:
            return self.residual_targets["medium"]
        else:
            return self.residual_targets["low"]

    def enrich_register(self, register: RiskRegister) -> RiskRegister:
        """Enrich all records in a risk register."""
        enriched_records = [self.enrich_record(record) for record in register.records]
        return RiskRegister(records=enriched_records)