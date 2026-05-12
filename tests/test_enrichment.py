"""Tests for risk and FMEA enrichment module."""

import json
import tempfile
from pathlib import Path

import pytest

from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher, FMEAScore
from eu_ai_act.compliance.risk import RiskConfig, RiskEnricher, RiskRecord, RiskRegister


class TestFMEAConfig:
    """Tests for FMEAConfig class."""

    def test_default_config_loading(self):
        """Test loading default configuration."""
        config = FMEAConfig()
        assert config.get_threshold("high") == 120
        assert config.get_threshold("medium") == 60
        assert config.get_threshold("low") == 20

    def test_domain_config_loading(self):
        """Test loading domain-specific configuration."""
        config = FMEAConfig(domain="radiology")
        root_causes = config.get_root_causes()
        assert "image_quality" in root_causes
        assert "dataset_bias" in root_causes

    def test_get_recommended_actions_high_rpn(self):
        """Test getting recommended actions for high RPN."""
        config = FMEAConfig(domain="radiology")
        actions = config.get_recommended_actions(150)
        assert len(actions) > 0
        assert any("dual" in action.lower() for action in actions)

    def test_get_recommended_actions_low_rpn(self):
        """Test getting recommended actions for low RPN."""
        config = FMEAConfig(domain="radiology")
        actions = config.get_recommended_actions(10)
        assert len(actions) > 0


class TestFMEAEnricher:
    """Tests for FMEAEnricher class."""

    def test_enrich_score_with_existing_data(self):
        """Test enriching a score that already has data."""
        config = FMEAConfig(domain="radiology")
        enricher = FMEAEnricher(config)

        score = FMEAScore(
            severity=5,
            occurrence=3,
            detectability=4,
            failure_mode="Prediction drift",
            root_cause="Data distribution shift",
            current_controls="Monitoring",
            recommended_actions="Retrain model",
        )

        enriched = enricher.enrich_score(score)
        assert enriched.root_cause == "Data distribution shift"
        assert enriched.current_controls == "Monitoring"
        assert enriched.action_priority is not None

    def test_enrich_score_without_data(self):
        """Test enriching a score without existing data."""
        config = FMEAConfig(domain="radiology")
        enricher = FMEAEnricher(config)

        score = FMEAScore(
            severity=8,
            occurrence=6,
            detectability=7,
            failure_mode="Missed pneumothorax",
        )

        enriched = enricher.enrich_score(score)
        assert enriched.root_cause is not None
        assert enriched.current_controls is not None
        assert enriched.action_priority == "high"  # RPN = 336

    def test_action_priority_determination(self):
        """Test action priority determination based on RPN."""
        config = FMEAConfig()
        enricher = FMEAEnricher(config)

        # High priority (RPN = 200)
        score_high = FMEAScore(severity=10, occurrence=5, detectability=4)
        enriched_high = enricher.enrich_score(score_high)
        assert enriched_high.action_priority == "high"

        # Medium priority (RPN = 80)
        score_medium = FMEAScore(severity=5, occurrence=4, detectability=4)
        enriched_medium = enricher.enrich_score(score_medium)
        assert enriched_medium.action_priority == "medium"

        # Low priority (RPN = 30)
        score_low = FMEAScore(severity=3, occurrence=5, detectability=2)
        enriched_low = enricher.enrich_score(score_low)
        assert enriched_low.action_priority == "low"

        # None priority (RPN = 10)
        score_none = FMEAScore(severity=2, occurrence=5, detectability=1)
        enriched_none = enricher.enrich_score(score_none)
        assert enriched_none.action_priority == "none"

    def test_enrich_scores_batch(self):
        """Test enriching multiple scores."""
        config = FMEAConfig(domain="radiology")
        enricher = FMEAEnricher(config)

        scores = [
            FMEAScore(severity=5, occurrence=3, detectability=4, failure_mode="Drift"),
            FMEAScore(severity=8, occurrence=6, detectability=7, failure_mode="Missed finding"),
        ]

        enriched = enricher.enrich_scores(scores)
        assert len(enriched) == 2
        assert all(score.action_priority is not None for score in enriched)


class TestRiskConfig:
    """Tests for RiskConfig class."""

    def test_default_thresholds(self):
        """Test default RPN thresholds."""
        config = RiskConfig()
        thresholds = config.get_rpn_thresholds()
        assert thresholds["high"] == 120
        assert thresholds["medium"] == 60
        assert thresholds["low"] == 20

    def test_residual_targets(self):
        """Test residual RPN targets."""
        config = RiskConfig()
        targets = config.get_residual_targets()
        assert targets["high"] == 80
        assert targets["medium"] == 40
        assert targets["low"] == 10


class TestRiskEnricher:
    """Tests for RiskEnricher class."""

    def test_enrich_record_with_controls(self):
        """Test enriching a record with existing controls."""
        config = RiskConfig()
        enricher = RiskEnricher(config)

        record = RiskRecord(
            risk_id="R-001",
            title="Test Risk",
            description="Test description",
            severity=5,
            occurrence=4,
            detectability=3,
            strategy="mitigate",
            current_controls="Dual-reader validation",
            recommended_action="Implement automated checks",
        )

        enriched = enricher.enrich_record(record)
        assert enriched.residual_rpn is not None
        assert enriched.residual_rpn < record.rpn
        assert enriched.mitigation_status == "applied"

    def test_enrich_record_without_controls(self):
        """Test enriching a record without controls."""
        config = RiskConfig()
        enricher = RiskEnricher(config)

        record = RiskRecord(
            risk_id="R-002",
            title="Test Risk",
            description="Test description",
            severity=5,
            occurrence=4,
            detectability=3,
            strategy="mitigate",
        )

        enriched = enricher.enrich_record(record)
        assert enriched.residual_rpn is None
        assert enriched.mitigation_status == "pending"

    def test_residual_rpn_calculation(self):
        """Test residual RPN calculation."""
        config = RiskConfig()
        enricher = RiskEnricher(config)

        # High RPN with comprehensive controls
        record = RiskRecord(
            risk_id="R-003",
            title="High Risk",
            description="Test",
            severity=10,
            occurrence=8,
            detectability=7,
            strategy="mitigate",
            current_controls="Dual-reader validation + automated thresholding",
        )

        enriched = enricher.enrich_record(record)
        assert enriched.residual_rpn is not None
        assert enriched.residual_rpn >= config.get_residual_targets()["high"]

    def test_enrich_register(self):
        """Test enriching an entire register."""
        config = RiskConfig()
        enricher = RiskEnricher(config)

        register = RiskRegister()
        register.add(RiskRecord(
            risk_id="R-001",
            title="Risk 1",
            description="Test",
            severity=5,
            occurrence=4,
            detectability=3,
            strategy="mitigate",
            current_controls="Control 1",
        ))
        register.add(RiskRecord(
            risk_id="R-002",
            title="Risk 2",
            description="Test",
            severity=8,
            occurrence=6,
            detectability=7,
            strategy="mitigate",
        ))

        enriched = enricher.enrich_register(register)
        assert len(enriched.records) == 2
        assert enriched.records[0].residual_rpn is not None
        assert enriched.records[1].residual_rpn is None


class TestFMEAScore:
    """Tests for FMEAScore class."""

    def test_rpn_calculation(self):
        """Test RPN calculation."""
        score = FMEAScore(severity=5, occurrence=4, detectability=3)
        assert score.rpn == 60

    def test_high_risk_threshold(self):
        """Test high risk threshold."""
        score_high = FMEAScore(severity=10, occurrence=5, detectability=4)
        assert score_high.high_risk is True

        score_low = FMEAScore(severity=3, occurrence=4, detectability=2)
        assert score_low.high_risk is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        score = FMEAScore(
            severity=5,
            occurrence=4,
            detectability=3,
            failure_mode="Test failure",
            root_cause="Test cause",
        )

        result = score.to_dict()
        assert result["severity"] == 5
        assert result["rpn"] == 60
        assert result["failure_mode"] == "Test failure"


class TestRiskRecord:
    """Tests for RiskRecord class."""

    def test_rpn_calculation(self):
        """Test RPN calculation."""
        record = RiskRecord(
            risk_id="R-001",
            title="Test",
            description="Test",
            severity=5,
            occurrence=4,
            detectability=3,
            strategy="mitigate",
        )
        assert record.rpn == 60

    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = RiskRecord(
            risk_id="R-001",
            title="Test Risk",
            description="Test description",
            severity=5,
            occurrence=4,
            detectability=3,
            strategy="mitigate",
        )

        result = record.to_dict()
        assert result["risk_id"] == "R-001"
        assert result["rpn"] == 60
        assert "created_at" in result
