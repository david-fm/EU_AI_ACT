# Clarity Audit - FMEA Report Quality Testing

This module provides a regression testing tool for evaluating the quality of AI-generated FMEA reports.

## Purpose

The Clarity Audit tool answers the question: **"Is this FMEA report good enough?"**

It is designed as a **warning-level regression test** that:
- Does NOT fail builds or CI pipelines
- Provides actionable feedback when report quality degrades
- Helps catch when system modifications negatively affect output quality

## Quick Start

### CLI Usage

```bash
# With notebook
uv run python -m eu_ai_act.testing.clarity_audit \
  --report outputs/run_01/assessment_enriched.md \
  --notebook case/train-simple-xray-cnn.ipynb

# With Python model file
uv run python -m eu_ai_act.testing.clarity_audit \
  --report outputs/run_01/assessment_enriched.md \
  --python src/models/my_model.py

# Custom threshold
uv run python -m eu_ai_act.testing.clarity_audit \
  --report outputs/run_01/assessment_enriched.md \
  --notebook case/train-simple-xray-cnn.ipynb \
  --threshold 8
```

### Python Usage

```python
from eu_ai_act.testing.clarity_audit import audit, ClarityResult

result = audit(
    report_path="outputs/run_01/assessment_enriched.md",
    notebook_path="case/train-simple-xray-cnn.ipynb",
)

if result.score >= 7:
    print("Report passes quality threshold")
else:
    print(f"Warning: Score {result.score}/10")
    for gap in result.gaps:
        print(f"  - {gap}")
```

## Scoring Criteria

| Score | Rating | Description |
|-------|--------|-------------|
| 10-9 | Excellent | Crystal clear, fully evidenced, immediately actionable |
| 8-7 | Good | Clear with minor gaps, generally actionable |
| 6-5 | Marginal | Some sections unclear or missing context |
| 4-3 | Poor | Significant gaps, hard to follow |
| 2-1 | Failing | Incomprehensible or completely lacks evidence |

## Output Schema

```python
@dataclass
class ClarityResult:
    understandable: bool     # Can domain expert follow the analysis?
    score: int              # 1-10 (>=7 passes)
    summary: str            # One-line assessment
    strengths: List[str]    # What works well
    gaps: List[str]         # What's missing or unclear
    missing_context: List[str]  # Model/data info from notebook NOT in report
    recommendations: List[str]  # How to improve
    is_actionable: bool     # Can compliance officer act on this?
```

## Warning Behavior

When score < 7, a `UserWarning` is issued with:
- Current score and threshold
- List of gaps
- Missing context from training setup
- Recommendations for improvement

The warning does NOT raise an exception or fail the test - it simply alerts.

## pytest Integration

```python
# tests/clarity/test_clarity_audit.py
import pytest
import warnings
from eu_ai_act.testing.clarity_audit import audit

class TestClarityAudit:
    @pytest.mark.slow
    def test_enriched_report_quality(self):
        """Real integration test (requires AI API)."""
        result = audit(
            report_path="outputs/real_integration_test/assessment_enriched_v2.md",
            notebook_path="case/train-simple-xray-cnn.ipynb",
            warn_threshold=7,
        )
        assert 1 <= result.score <= 10
        if result.score < 7:
            warnings.warn(f"Report quality degraded: {result.summary}")
```

Run with:
```bash
uv run pytest tests/clarity/ -v
uv run pytest tests/clarity/ -v -m "not slow"  # Skip real API tests
uv run pytest tests/clarity/ -v -m slow       # Only real API tests
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     ClarityAuditAgent                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Parse notebook/Python file → extract model info              │
│     - Architecture (MobileNet, ResNet, etc.)                     │
│     - Dataset (NIH Chest X-rays, etc.)                          │
│     - Training params (batch size, epochs, etc.)                │
│                                                                  │
│  2. Read FMEA markdown report                                    │
│                                                                  │
│  3. Send to AI auditor agent with:                               │
│     - Model context                                              │
│     - Report content                                            │
│     - Evaluation criteria (understandable, actionable, etc.)    │
│                                                                  │
│  4. AI agent returns structured JSON:                           │
│     - understandable: bool                                      │
│     - score: 1-10                                               │
│     - strengths, gaps, missing_context, recommendations        │
│                                                                  │
│  5. If score < 7 → issue warning                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Notebook Parsing

The agent extracts from Jupyter notebooks:
- `from tensorflow.keras.applications import X` → architecture
- `TRAIN_BATCH_SIZE = N` → batch size
- `NIH`, `Chest X-ray` → dataset type
- `mixed_precision`, `early_stopping` → training features

## Python File Parsing

From Python files, it extracts:
- `model_name` patterns (MobileNet, ResNet, EfficientNet)
- `batch_size = N` / `batch_size=N` → batch size
- `epochs = N` / `epochs=N` → epochs
- TensorFlow/PyTorch imports
- Dataset names

## Files

```
src/eu_ai_act/testing/
  └── clarity_audit.py       # Main module (ClarityAuditAgent, audit(), ClarityResult)

tests/clarity/
  ├── conftest.py           # pytest fixtures
  └── test_clarity_audit.py # Unit + integration tests
```

## Use Cases

1. **Regression testing after enrichment changes** - Run before/after FMEAEnricher modifications
2. **PR review** - Automated comment on report quality
3. **Quality gates** - Ensure all reports meet minimum quality bar
4. **Debugging** - Understand why a report is unclear by reading gaps/recommendations

## Limitations

- Requires AI API access (not available offline)
- Parsing is regex-based, may miss unusual notebook structures
- Score is subjective (depends on AI model opinions)
- No baseline comparison - each report judged on its own merits