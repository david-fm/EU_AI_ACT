"""Risk register primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal


RiskStrategy = Literal["eliminate", "mitigate", "inform"]


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