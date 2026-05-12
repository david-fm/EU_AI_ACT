# Module 1 - Risk FMEA Enrichment Documentation

This documentation covers the Risk and FMEA enrichment module for the EU AI Act compliance toolkit.

## System Architecture

This is a **unified multi-phase system** with AI-powered analysis:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ASSESSMENT PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 0: Evaluation (Module 0)                                            │
│  ┌───────────────┐    ┌───────────────┐    ┌─────────────────────────────┐  │
│  │ Model + Data  │───▶│ Compliance    │───▶│ Baseline Assessment JSON  │  │
│  │ Assessment    │    │ Evaluator     │    │ (fmea_scores, risk_register,│  │
│  └───────────────┘    └───────────────┘    │ fairness, stress results)  │  │
│                                            └─────────────────────────────┘  │
│                                                      │                       │
│                                                      ▼                       │
│  Phase 1: AI-Powered Enrichment (Module 1)          │                       │
│  ┌──────────────────────────────────────────────────┴───────────────────┐  │
│  │  FMEAEnricher (always AI-powered)                                   │  │
│  │  - Receives full assessment context (fairness, stress, risk)        │  │
│  │  - Uses domain taxonomy for classification                          │  │
│  │  - Generates evidence-based root cause analysis                    │  │
│  │  - Outputs: root_cause_category, root_cause_analysis,               │  │
│  │             recommended_actions, mitigation_strategy,               │  │
│  │             monitoring_recommendations, evidence_from_data          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  Phase 2: Export                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  export_report.py (unified exporter)                                 │  │
│  │  - JSON, Markdown, PDF                                                │  │
│  │  - Detects AI-enriched vs baseline                                   │  │
│  │  - Shows [AI] badges and provenance                                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Documentation Structure

### [Configuration Guide](./CONFIGURATION.md)
- How to configure risk thresholds and FMEA parameters
- TOML configuration file structure
- All available configuration options explained

### [Domain-Specific Configuration](./DOMAIN_CONFIGS.md)
- How to create domain-specific configurations
- **Taxonomy-based design** (not prescriptive lists)
- Radiology domain example
- Steps to add new domains

### [CLI Usage](./CLI_USAGE.md)
- Command-line interface reference for enrichment
- Examples for basic and advanced usage
- Environment variables and API configuration
- **Note:** AI is always enabled (no `--use-ai` flag)

### [Export System](./EXPORT_SYSTEM.md)
- Unified export pipeline for baseline and AI-enriched assessments
- Export to JSON, Markdown, and PDF formats
- Single command for all formats
- Provenance tracking ([AI] vs [Rule] badges)

### [AI Integration](./AI_INTEGRATION.md)
- How the Agno AI agent generates insights
- Full assessment context (fairness, stress, risk register)
- Evidence-based analysis with data citations
- Supported AI providers and configuration

## Quick Start

### Phase 1: Run Assessment (Module 0)
```bash
uv run python -m eu_ai_act.cli \
  --framework keras \
  --model-path models/nih-mobilenet.h5 \
  --input data/nih_chest_xray.json \
  --output-dir outputs/run_01
```

### Phase 2: Enrichment (Module 1)
```bash
# AI is always enabled - just specify domain
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology
```

### Phase 3: Export (Unified)
```bash
# Export all formats (PDF, MD, JSON)
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --output-dir outputs/run_01/reports
```

## What This Module Does

1. **AI-Powered FMEA Enrichment**: Generates detailed root cause analysis using actual assessment data
2. **Evidence-Based Analysis**: AI cites specific data points (e.g., "senior TPR gap of 0.285")
3. **Taxonomy Classification**: Root causes classified into domain-specific categories
4. **Action Taxonomy**: Recommended actions from domain-defined action types
5. **Comprehensive Output**: Mitigation strategy, monitoring recommendations, evidence citations
6. **Unified Export**: Single pipeline exports to JSON, Markdown, and PDF formats

## File Structure

```
docs/02_MODULO_1_RIESGO_FMEA/
├── README.md              # This file
├── CONFIGURATION.md       # Risk and FMEA configuration guide
├── DOMAIN_CONFIGS.md      # Domain-specific setup guide (taxonomy-based)
├── CLI_USAGE.md           # CLI reference (AI always enabled)
├── EXPORT_SYSTEM.md       # Unified export system
└── AI_INTEGRATION.md      # AI agent configuration and workflow

scripts/
├── enriquecer_riesgo.py   # Enrichment CLI (Phase 1)
└── export_report.py       # Unified export CLI (Phase 2)

src/eu_ai_act/compliance/
├── fmea.py                # FMEAConfig, FMEAEnricher, FMEAScore
├── risk.py                # RiskConfig, RiskEnricher, RiskRecord
└── ai_insights.py         # FMEAAIAgent, FMEAInsightGenerator

config/
├── risk.toml              # Default thresholds and targets
└── domains/
    └── radiology.toml     # Radiology taxonomy (root_cause_taxonomy, action_taxonomy)
```

## Dependencies

- `agno>=1.0.0` - For AI-powered text generation
- `python-dotenv` - For loading environment variables
- `reportlab` - For PDF generation
- `pydantic` - For structured AI output validation
- `tomllib` (stdlib) - For TOML configuration parsing

## Key Changes from Previous Version

| Feature | Before | After |
|---------|--------|-------|
| AI Mode | Optional (`--use-ai` flag) | Always enabled |
| Fallback | Rule-based when AI unavailable | No fallback (AI required) |
| Root Causes | Prescriptive lists in config | Taxonomy categories for classification |
| Actions | RPN-based predefined lists | Action taxonomy for AI to customize |
| Assessment Context | Single failure mode only | Full context (fairness, stress, risk) |
| Output | 4 basic fields | 8 fields including evidence citations |

## Backward Compatibility

The export system maintains backward compatibility:
- Baseline assessments (from Module 0) can be exported directly
- AI-enriched assessments include provenance tracking
- Exporters automatically detect and render appropriate fields

## Related Documentation

- [EU AI Act Compliance Module 0](../00_MODULO_0_EVALUACION/) - Model and data evaluation
- [EU AI Act Article 9](https://eur-ai-act.eu/article-9) - Risk management system requirements
- [ISO 14971](https://www.iso.org/standard/72704.html) - Risk management for medical devices