# Project Summary: EU AI ACT Compliance Evaluator

## Project Purpose

This is a Python toolkit for evaluating compliance of computer vision models against EU AI Act requirements. It assesses models built with Keras, TensorFlow, or PyTorch and generates structured compliance reports.

## Core Functionality

The toolkit runs a multi-faceted compliance evaluation that includes:

1. **Risk Register** - Identifies and catalogs operational risks with severity, occurrence, and detectability scores
2. **FMEA Analysis** - Failure Mode and Effects Analysis computing RPN (Risk Priority Number) scores
3. **Fairness Evaluation** - Analyzes model predictions across sensitive metadata groups (gender, age, view position)
4. **Stress Testing** - Tests model robustness against domain-specific perturbations (noise, blur, occlusion, illumination)
5. **Export** - Generates assessment reports in JSON, Markdown, and PDF formats

## How It Works

### CLI Execution
```bash
uv run eu-ai-act \
    --framework keras \
    --model-path case/xray_class.weights.h5 \
    --input path/to/dataset.json \
    --output-dir outputs/run_01
```

### Pipeline Flow
1. Load model via framework-specific adapter (Keras/TensorFlow/PyTorch)
2. Load dataset via JSON/CSV adapter with metadata support
3. Run batch predictions through the model
4. Evaluate fairness metrics per metadata field using fairlearn
5. Run stress tests with configurable domain taxonomies
6. Build risk register with automatic risk detection
7. Generate FMEA scores based on prediction quality
8. Export results to JSON, Markdown, and PDF

### Output Artifacts
- `assessment.json` - Complete structured data with all metrics
- `assessment.md` - Human-readable markdown report
- `assessment.pdf` - Formatted PDF document

Each run gets a unique `run_id` and `config_hash` for versioning and comparison with previous runs.

## Architecture

```
src/eu_ai_act/
├── adapters/           # Framework adapters (Keras, TensorFlow, PyTorch)
├── compliance/          # Risk, FMEA, Fairness, Stress, Taxonomy modules
├── evaluation/          # Pipeline orchestrator
├── reporting/           # Exporters (JSON, MD, PDF)
├── data/                # Dataset loading
└── cli.py              # Command-line interface
```

## Key Technologies

| Category | Library |
|----------|---------|
| ML Frameworks | Keras 3.12.0, TensorFlow-macos 2.16+, PyTorch 2.11+ |
| Fairness | fairlearn 0.12+ |
| Data | pandas, polars, scikit-learn |
| Visualization | matplotlib, graphviz, reportlab |
| Testing | pytest, pytest-cov |
| Package Manager | uv |

## Input Requirements

- **Model**: Serialized model file (.h5, .pt, etc.)
- **Dataset**: JSON or CSV with features, labels, and metadata columns
- **Taxonomy**: Optional TOML file defining domain-specific stress test cases

## Current Status

- Functional CLI with JSON/MD/PDF exports
- Integration tested with real X-ray classification model
- Fairness analysis by gender, age group, and view position
- Stress testing for radiology domain (sensor noise, blur, occlusion, low light)
- Run versioning with comparison support between runs

## Module 1 - FMEA Risk Enrichment (AI-Powered)

The FMEA enrichment module (`docs/02_MODULO_1_RIESGO_FMEA/`) extends baseline assessments with AI-powered insights:

### Features
- **AI-Powered Analysis**: Uses Agno agent to generate detailed root cause analysis
- **Evidence-Based**: AI cites specific data points from assessment metrics
- **Taxonomy-Based**: Domain-specific root cause and action taxonomies
- **Unified Export**: Single pipeline for baseline and enriched reports

### Components
- `src/eu_ai_act/compliance/fmea.py` - FMEAConfig, FMEAEnricher, FMEAScore
- `src/eu_ai_act/compliance/ai_insights.py` - FMEAAIAgent with full assessment context
- `src/eu_ai_act/testing/clarity_audit.py` - Regression testing tool for report quality

### Output Fields (AI-Generated)
| Field | Description |
|-------|-------------|
| `root_cause_category` | Taxonomy classification (e.g., dataset_bias) |
| `root_cause_analysis` | Evidence-based analysis citing specific metrics |
| `recommended_actions` | Targeted actions from action taxonomy |
| `mitigation_strategy` | EU AI Act Article 9 aligned approach |
| `monitoring_recommendations` | Metrics, frequencies, acceptance criteria |
| `evidence_from_data` | Data citations informing the analysis |

### Testing
```bash
# Run clarity audit (regression test for report quality)
uv run pytest tests/clarity/ -v -m "not slow"
uv run pytest tests/clarity/ -v -m slow  # Requires AI API

# CLI usage
uv run python -m eu_ai_act.testing.clarity_audit \
  --report outputs/run_01/assessment_enriched.md \
  --notebook case/train-simple-xray-cnn.ipynb
```

See `docs/02_MODULO_1_RIESGO_FMEA/README.md` for full documentation.