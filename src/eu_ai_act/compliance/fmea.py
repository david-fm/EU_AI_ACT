"""FMEA scoring helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

import tomllib
from pathlib import Path

from .ai_insights import FMEAInsightGenerator


@dataclass(frozen=True, slots=True)
class FMEAScore:
    severity: int
    occurrence: int
    detectability: int
    failure_mode: str | None = None
    root_cause_category: str | None = None
    root_cause: str | None = None
    current_controls: str | None = None
    recommended_actions: str | None = None
    mitigation_strategy: str | None = None
    monitoring_recommendations: str | None = None
    evidence_from_data: list[str] | None = None
    residual_rpn: int | None = None
    action_required: bool = False
    action_priority: str | None = None
    insights_source: Literal["ai", "rule_based"] = "rule_based"

    @property
    def rpn(self) -> int:
        return self.severity * self.occurrence * self.detectability

    @property
    def high_risk(self) -> bool:
        return self.rpn >= 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "occurrence": self.occurrence,
            "detectability": self.detectability,
            "rpn": self.rpn,
            "failure_mode": self.failure_mode,
            "root_cause_category": self.root_cause_category,
            "root_cause": self.root_cause,
            "current_controls": self.current_controls,
            "recommended_actions": self.recommended_actions,
            "mitigation_strategy": self.mitigation_strategy,
            "monitoring_recommendations": self.monitoring_recommendations,
            "evidence_from_data": self.evidence_from_data,
            "residual_rpn": self.residual_rpn,
            "high_risk": self.high_risk,
            "action_required": self.action_required,
            "action_priority": self.action_priority,
            "insights_source": self.insights_source,
        }


class FMEAConfig:
    """Configuration loader for FMEA enrichment."""

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

    def get_threshold(self, level: str) -> int:
        """Get RPN threshold for action priority level."""
        thresholds = self._config.get("fmea", {}).get("action_priority", {})
        return thresholds.get(level, {}).get("min_rpn", 0)

    def get_root_cause_taxonomy(self) -> dict[str, str]:
        """Get domain-specific root cause taxonomy (category → description)."""
        return self._domain_config.get("fmea", {}).get("root_cause_taxonomy", {})

    def get_action_taxonomy(self) -> dict[str, str]:
        """Get domain-specific action taxonomy (type → description)."""
        return self._domain_config.get("fmea", {}).get("action_taxonomy", {})

    def get_failure_mode_config(self) -> dict[str, str]:
        """Get domain-specific failure mode configuration."""
        return self._domain_config.get("fmea", {}).get("failure_modes", {})


class FMEAEnricher:
    """Enriches FMEA scores with domain-specific information."""

    def __init__(self, config: FMEAConfig, use_ai: bool = True, model_id: str = "deepseek-v4-flash", api_key: str | None = None, base_url: str = "https://opencode.ai/zen/go/v1"):
        self.config = config
        self.use_ai = use_ai
        self.ai_generator = FMEAInsightGenerator(use_ai=use_ai, model_id=model_id, api_key=api_key, base_url=base_url) if use_ai else None

    def enrich_score(self, score: FMEAScore) -> FMEAScore:
        """Enrich a single FMEA score with domain-specific data (rule-based fallback)."""
        rpn = score.rpn
        action_priority = self._determine_action_priority(rpn)
        recommended_actions = self._generate_recommended_actions(score, rpn)
        root_cause = self._enrich_root_cause(score)
        current_controls = self._enrich_current_controls(score)

        return FMEAScore(
            severity=score.severity,
            occurrence=score.occurrence,
            detectability=score.detectability,
            failure_mode=score.failure_mode,
            root_cause_category=None,
            root_cause=root_cause,
            current_controls=current_controls,
            recommended_actions=recommended_actions,
            mitigation_strategy=None,
            monitoring_recommendations=None,
            evidence_from_data=None,
            residual_rpn=score.residual_rpn,
            action_required=rpn >= self.config.get_threshold("medium"),
            action_priority=action_priority,
            insights_source="rule_based",
        )

    async def enrich_score_with_ai(self, score: FMEAScore, assessment: dict) -> FMEAScore:
        """Enrich a single FMEA score with AI-generated insights using full assessment context."""
        if not self.use_ai or not self.ai_generator:
            return self.enrich_score(score)

        rpn = score.rpn
        action_priority = self._determine_action_priority(rpn)

        insights = await self.ai_generator.generate_insights(
            failure_mode=score.failure_mode or "Unknown failure mode",
            severity=score.severity,
            occurrence=score.occurrence,
            detectability=score.detectability,
            domain=self.config.domain,
            fairness_results=assessment.get("fairness_results", []),
            stress_results=assessment.get("stress_results", []),
            risk_register=assessment.get("risk_register", {}).get("records", []),
            existing_controls=score.current_controls,
            root_cause_taxonomy=self.config.get_root_cause_taxonomy(),
            action_taxonomy=self.config.get_action_taxonomy(),
        )

        return FMEAScore(
            severity=score.severity,
            occurrence=score.occurrence,
            detectability=score.detectability,
            failure_mode=score.failure_mode,
            root_cause_category=insights.get("root_cause_category"),
            root_cause=insights.get("root_cause_analysis"),
            current_controls=score.current_controls,
            recommended_actions="; ".join(insights.get("recommended_actions", [])) if insights.get("recommended_actions") else None,
            mitigation_strategy=insights.get("mitigation_strategy"),
            monitoring_recommendations="; ".join(insights.get("monitoring_recommendations", [])) if insights.get("monitoring_recommendations") else None,
            evidence_from_data=insights.get("evidence_from_data"),
            residual_rpn=score.residual_rpn,
            action_required=rpn >= self.config.get_threshold("medium"),
            action_priority=action_priority,
            insights_source="ai",
        )

    def _determine_action_priority(self, rpn: int) -> str:
        """Determine action priority based on RPN."""
        if rpn >= self.config.get_threshold("high"):
            return "high"
        elif rpn >= self.config.get_threshold("medium"):
            return "medium"
        elif rpn >= self.config.get_threshold("low"):
            return "low"
        else:
            return "none"

    def _generate_recommended_actions(self, score: FMEAScore, rpn: int) -> str:
        """Generate recommended actions based on score and RPN (rule-based fallback)."""
        taxonomy = self.config.get_action_taxonomy()
        if not taxonomy:
            return score.recommended_actions or "No specific actions recommended"

        actions = []
        if rpn >= self.config.get_threshold("high"):
            actions.extend([
                "Implement immediate corrective actions",
                "Establish cross-functional review team",
                "Enhance monitoring and detection capabilities",
            ])
        elif rpn >= self.config.get_threshold("medium"):
            actions.extend([
                "Review and enhance existing controls",
                "Implement additional monitoring",
                "Schedule periodic risk reviews",
            ])
        else:
            actions.extend([
                "Monitor through existing controls",
                "Schedule routine reviews",
                "Document known limitations",
            ])

        return "; ".join(actions)

    def _enrich_root_cause(self, score: FMEAScore) -> str:
        """Enrich root cause with domain-specific taxonomy (rule-based fallback)."""
        if score.root_cause:
            return score.root_cause

        taxonomy = self.config.get_root_cause_taxonomy()
        if not taxonomy:
            return "Unknown root cause"

        if score.failure_mode:
            failure_mode_lower = score.failure_mode.lower()
            for category in taxonomy.keys():
                if any(keyword in failure_mode_lower for keyword in category.split("_")):
                    return f"{category.replace('_', ' ').title()}: see taxonomy for details"

        return "Domain-specific root cause analysis required"

    def _enrich_current_controls(self, score: FMEAScore) -> str:
        """Enrich current controls with domain-specific information."""
        if score.current_controls:
            return score.current_controls

        failure_mode_config = self.config.get_failure_mode_config()
        if failure_mode_config:
            return failure_mode_config.get("control", "Standard quality controls")

        return "Standard quality controls"

    def enrich_scores(self, scores: list[FMEAScore]) -> list[FMEAScore]:
        """Enrich a list of FMEA scores (rule-based)."""
        return [self.enrich_score(score) for score in scores]

    async def enrich_scores_with_ai(self, scores: list[FMEAScore], assessment: dict) -> list[FMEAScore]:
        """Enrich a list of FMEA scores with AI insights using full assessment context."""
        if not self.use_ai:
            return self.enrich_scores(scores)

        enriched_scores = []
        for score in scores:
            enriched_score = await self.enrich_score_with_ai(score, assessment)
            enriched_scores.append(enriched_score)

        return enriched_scores