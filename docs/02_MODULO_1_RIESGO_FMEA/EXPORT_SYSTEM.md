# Export System - Unified Reporting Pipeline

This document explains the unified export system that handles both baseline assessments (from Module 0) and enriched assessments (from Module 1).

## Overview

The export system is designed as a **single pipeline** that automatically detects the assessment type and includes the appropriate fields in each output format.

```
┌─────────────────────────────────────────────────────────────┐
│                    Assessment JSON                            │
│  (baseline or enriched)                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   Automatic Detection        │
              │   is_enriched() function     │
              └─────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
    ┌─────────────────┐           ┌─────────────────┐
    │ Baseline       │           │ Enriched        │
    │ Assessment     │           │ (AI-Powered)    │
    └─────────────────┘           └─────────────────┘
            │                               │
            └───────────────┬───────────────┘
                            │
                            ▼
          ┌──────────────────────────────────────┐
          │  Unified Exporter (export_report.py)│
          └──────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
      ┌─────────┐    ┌─────────┐    ┌─────────┐
      │   PDF   │    │   MD    │    │   JSON  │
      └─────────┘    └─────────┘    └─────────┘
```

## How Detection Works

The `is_enriched()` function checks for enriched FMEA fields:

```python
def _is_enriched(report: dict) -> bool:
    fmea_scores = report.get("fmea_scores", [])
    if not fmea_scores:
        return False
    first_score = fmea_scores[0]
    return "action_priority" in first_score or "root_cause" in first_score
```

The `has_ai_insights()` function checks for AI-generated content:

```python
def _has_ai_insights(report: dict) -> bool:
    fmea_scores = report.get("fmea_scores", [])
    if not fmea_scores:
        return False
    return any(s.get("insights_source") == "ai" for s in fmea_scores)
```

## Output Formats

### JSON
- Always includes all fields from the input
- No transformation, just pretty-printing
- Suitable for programmatic processing

### Markdown
- Structured with headers and bullet points
- **AI-enriched assessments**: Includes `[AI]` badge and all AI-generated fields
- **Baseline assessments**: Standard risk register format

### PDF
- Styled tables with color-coded risk levels
- **AI-enriched assessments**:
  - Section 1: Risk Register (with residual RPN, mitigation status)
  - Section 2: FMEA Analysis with AI badge, showing:
    - Root Cause Category
    - Root Cause Analysis (full text)
    - Recommended Actions
    - Mitigation Strategy
    - Monitoring Recommendations
    - Evidence from Data
  - Section 3: Stress Testing
  - Section 4: Fairness
  - Section 5: Transparency
- **Baseline assessments**:
  - Section 1: Risk Register (original fields)
  - Section 2: Stress Testing
  - Section 3: Fairness
  - Section 4: Transparency

## CLI Usage

### Export All Formats

```bash
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --output-dir outputs/run_01/reports
```

Output:
```
Assessment type: Enriched
Exported files:
  - PDF: outputs/run_01/reports/assessment_enriched.pdf
  - MD: outputs/run_01/reports/assessment_enriched.md
  - JSON: outputs/run_01/reports/assessment_enriched.json
```

### Export Specific Format

```bash
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --format pdf \
  --output outputs/run_01/reports/report.pdf
```

### Custom Base Name

```bash
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --output-dir outputs/run_01/reports \
  --base-name final_report
```

## Programmatic Usage

```python
from scripts.export_report import load_assessment, export_pdf, export_markdown, export_json

data = load_assessment(Path("assessment_enriched.json"))

# Export to specific format
export_pdf(data, Path("report.pdf"))
export_markdown(data, Path("report.md"))
export_json(data, Path("report.json"))

# Check assessment type
from scripts.export_report import _is_enriched, _has_ai_insights
is_enriched = _is_enriched(data)
has_ai = _has_ai_insights(data)
```

## Fields by Assessment Type

### Baseline Assessment Fields

**Risk Register:**
- risk_id, title, description
- severity, occurrence, detectability
- rpn, high_risk
- strategy
- cause, recommended_action

**FMEA Scores:**
- failure_mode
- severity, occurrence, detectability
- rpn

### AI-Enriched Assessment Fields

**FMEA Scores (AI-generated):**
| Field | Description |
|-------|-------------|
| `root_cause_category` | Taxonomy category (e.g., "dataset_bias") |
| `root_cause` | Evidence-based analysis citing specific data |
| `recommended_actions` | Actions from taxonomy, customized |
| `mitigation_strategy` | EU AI Act Article 9 aligned strategy |
| `monitoring_recommendations` | Metrics, frequencies, acceptance criteria |
| `evidence_from_data` | Data citations that informed analysis |
| `insights_source` | Always "ai" |
| `action_priority` | high/medium/low/none |
| `action_required` | boolean |

**Risk Register (rule-based enrichment):**
- mitigation_status (pending/applied/verified)
- residual_rpn
- current_controls

## PDF Styling

The PDF export uses consistent styling:

| Element | Color | Notes |
|---------|-------|-------|
| High Risk | Red (#e74c3c) | Risk status badge |
| Mitigated Risk | Green (#27ae60) | Risk status badge |
| High Priority | Red (#c0392b) | FMEA action priority |
| Medium Priority | Orange (#d35400) | FMEA action priority |
| Low Priority | Green (#27ae60) | FMEA action priority |
| AI Badge | Purple (#6c5ce7) | AI-powered analysis indicator |
| Evidence | Purple (#6c5ce7) | AI evidence citations |
| Section Headers | Dark Blue (#2c3e50) | Bold, 11pt |
| Labels | Gray (#6c757d) | 8pt |
| Values | Dark (#2c3e50) | Bold, 9pt |

## Integration with CLI

The export script is integrated into the main CLI workflow:

```bash
# Full pipeline

# Step 1: Run assessment (Module 0)
uv run python -m eu_ai_act.cli \
  --framework keras \
  --model-path models/model.h5 \
  --input data/dataset.json \
  --output-dir outputs/run_01

# Step 2: Enrich with AI (Module 1) - AI is always enabled
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology

# Step 3: Export reports
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --output-dir outputs/run_01/reports
```

## Provenance Tracking

AI-generated assessments include `insights_source` field to track provenance:

```json
{
  "fmea_scores": [{
    "failure_mode": "Prediction quality drift",
    "root_cause": "Dataset bias evidenced by...",
    "insights_source": "ai"
  }]
}
```

This allows auditors to distinguish between:
- AI-generated insights (source: "ai")
- Rule-based analysis (source: "rule_based")

## Related Documentation

- [CLI Usage](./CLI_USAGE.md) - Enrichment CLI reference
- [Configuration Guide](./CONFIGURATION.md) - Configuration file format
- [AI Integration](./AI_INTEGRATION.md) - AI configuration details