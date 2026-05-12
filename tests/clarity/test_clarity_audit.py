"""Clarity audit tests for FMEA reports."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eu_ai_act.testing.clarity_audit import ClarityAuditAgent, ClarityResult, audit


class TestClarityAudit:
    """Tests for clarity audit functionality."""

    @pytest.fixture
    def sample_report(self, tmp_path: Path) -> Path:
        """Create a sample FMEA report for testing."""
        content = """# Compliance Assessment: test-model

## 1. Risk Register
### R-1: Fairness disparity
- Severity: 5
- Occurrence: 4
- RPN: 80

## 2. FMEA Analysis
### FMEA #1
- Failure Mode: Prediction quality drift
- Root Cause: Dataset bias evidenced by TPR gap of 0.285
- Recommended Actions: Retrain with balanced data
- Mitigation Strategy: Monitor per-group metrics quarterly
- Evidence: Age group TPR young=0.611, senior=0.326
"""
        path = tmp_path / "report.md"
        path.write_text(content)
        return path

    @pytest.fixture
    def sample_notebook(self, tmp_path: Path) -> Path:
        """Create a sample notebook for testing."""
        import json

        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": [
                        "from tensorflow.keras.applications import MobileNet\n",
                        "model = MobileNet(weights='imagenet')\n",
                        "TRAIN_BATCH_SIZE = 64\n",
                    ],
                },
                {
                    "cell_type": "markdown",
                    "source": ["# Training NIH Chest X-rays\n"],
                },
            ]
        }
        path = tmp_path / "train.ipynb"
        with open(path, "w") as f:
            json.dump(notebook, f)
        return path

    @pytest.fixture
    def sample_python_model(self, tmp_path: Path) -> Path:
        """Create a sample Python model file for testing."""
        content = '''
"""Simple CNN model for testing."""

import tensorflow as tf
from tensorflow import keras

def create_model():
    model = keras.Sequential([
        keras.layers.Conv2D(32, 3, activation='relu'),
        keras.layers.MaxPooling2D(),
        keras.layers.Flatten(),
        keras.layers.Dense(10, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', batch_size=32, epochs=10)
    return model
'''
        path = tmp_path / "model.py"
        path.write_text(content)
        return path

    def test_parse_notebook(self, sample_notebook: Path):
        """Test notebook parsing extracts model info."""
        agent = ClarityAuditAgent()
        result = asyncio.run(agent._parse_notebook(sample_notebook))

        assert result["model_architecture"] == "MobileNet"
        assert result["training_params"]["train_batch_size"] == 64
        assert "MobileNet backbone" in result["key_components"]

    def test_parse_python_file(self, sample_python_model: Path):
        """Test Python file parsing extracts model info."""
        agent = ClarityAuditAgent()
        result = asyncio.run(agent._parse_python_file(sample_python_model))

        assert "TensorFlow/Keras" in result["key_components"]
        assert result["training_params"]["batch_size"] == 32
        assert result["training_params"]["epochs"] == 10

    def test_load_model_info_from_notebook(self, sample_notebook: Path):
        """Test model info loading from notebook."""
        agent = ClarityAuditAgent()
        info = asyncio.run(agent._load_model_info(notebook_path=sample_notebook))

        assert "MobileNet" in info
        assert "64" in info

    def test_load_model_info_from_python(self, sample_python_model: Path):
        """Test model info loading from Python file."""
        agent = ClarityAuditAgent()
        info = asyncio.run(agent._load_model_info(python_path=sample_python_model))

        assert "TensorFlow/Keras" in info

    def test_clarity_result_validation(self):
        """Test ClarityResult validates score range."""
        with pytest.raises(ValueError):
            ClarityResult(
                understandable=True,
                score=11,
                summary="test",
                strengths=[],
                gaps=[],
                missing_context=[],
                recommendations=[],
                is_actionable=True,
            )

    def test_clarity_result_valid(self):
        """Test ClarityResult accepts valid scores."""
        result = ClarityResult(
            understandable=True,
            score=7,
            summary="Passes threshold",
            strengths=["Clear"],
            gaps=["Minor gap"],
            missing_context=[],
            recommendations=["Fix gap"],
            is_actionable=True,
        )
        assert result.score == 7
        assert result.understandable is True

    def test_audit_async_with_mock(self, sample_report: Path, sample_notebook: Path):
        """Test audit async method with mock."""
        agent = ClarityAuditAgent()

        mock_response = MagicMock()
        mock_response.content = '{"understandable": true, "score": 8, "summary": "Good report", "strengths": ["Clear"], "gaps": [], "missing_context": [], "recommendations": [], "is_actionable": true}'

        async def mock_arun(prompt):
            return mock_response

        with patch.object(agent.agent, "arun", side_effect=mock_arun):
            result = asyncio.run(agent.audit(sample_report, sample_notebook))

        assert isinstance(result, ClarityResult)
        assert result.score == 8
        assert result.understandable is True
        assert result.is_actionable is True

    def test_audit_sync_warns_below_threshold(self, sample_report: Path, sample_notebook: Path):
        """Test audit() issues warning when score < threshold."""
        mock_result = ClarityResult(
            understandable=False,
            score=5,
            summary="Poor",
            strengths=[],
            gaps=["Unclear"],
            missing_context=[],
            recommendations=[],
            is_actionable=False,
        )

        with patch("eu_ai_act.testing.clarity_audit.asyncio.run", return_value=mock_result):
            with pytest.warns(UserWarning, match="Score 5/10"):
                result = audit(
                    report_path=sample_report,
                    notebook_path=sample_notebook,
                )
                assert result.score < 7

    def test_audit_sync_no_warn_above_threshold(self, sample_report: Path, sample_notebook: Path):
        """Test audit() does not warn when score >= threshold."""
        import warnings

        mock_result = ClarityResult(
            understandable=True,
            score=8,
            summary="Good",
            strengths=["Clear"],
            gaps=[],
            missing_context=[],
            recommendations=[],
            is_actionable=True,
        )

        with patch("eu_ai_act.testing.clarity_audit.asyncio.run", return_value=mock_result):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = audit(
                    report_path=sample_report,
                    notebook_path=sample_notebook,
                    warn_threshold=7,
                )
                clarity_warnings = [x for x in w if "Clarity audit WARNING" in str(x.message)]
                assert len(clarity_warnings) == 0
                assert result.score >= 7

    def test_audit_sync_no_warn_at_threshold(self, sample_report: Path, sample_notebook: Path):
        """Test audit() does not warn when score == threshold."""
        import warnings

        mock_result = ClarityResult(
            understandable=True,
            score=7,
            summary="Pass",
            strengths=["Clear"],
            gaps=["Minor gap"],
            missing_context=[],
            recommendations=[],
            is_actionable=True,
        )

        with patch("eu_ai_act.testing.clarity_audit.asyncio.run", return_value=mock_result):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = audit(
                    report_path=sample_report,
                    notebook_path=sample_notebook,
                    warn_threshold=7,
                )
                clarity_warnings = [x for x in w if "Clarity audit WARNING" in str(x.message)]
                assert len(clarity_warnings) == 0
                assert result.score == 7


class TestClarityAuditIntegration:
    """Integration tests that require real notebook and report files."""

    @pytest.fixture
    def real_notebook(self) -> Path:
        """Path to real training notebook."""
        return Path(__file__).parent.parent.parent / "case" / "train-simple-xray-cnn.ipynb"

    @pytest.fixture
    def real_report(self) -> Path:
        """Path to real enriched report."""
        return (
            Path(__file__).parent.parent.parent
            / "outputs"
            / "real_integration_test"
            / "assessment_enriched_v2.md"
        )

    def test_real_files_exist(self, real_notebook: Path, real_report: Path):
        """Verify test fixtures exist."""
        assert real_notebook.exists(), f"Notebook not found: {real_notebook}"
        assert real_report.exists(), f"Report not found: {real_report}"

    @pytest.mark.slow
    def test_audit_real_report(self, real_notebook: Path, real_report: Path):
        """Test audit on real files (requires AI API)."""
        import warnings

        result = audit(
            report_path=real_report,
            notebook_path=real_notebook,
            warn_threshold=7,
        )

        assert isinstance(result, ClarityResult)
        assert 1 <= result.score <= 10

        if result.score < 7:
            warnings.warn(f"Report scored {result.score}/10 - below threshold 7")
            assert len(result.gaps) > 0, "Low score but no gaps reported"