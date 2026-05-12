# CLI Usage Guide - Risk FMEA Enrichment

This document provides a complete reference for the command-line interface.

## Command Syntax

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input <path> \
  --output <path> \
  [--domain <domain>] \
  [--config <path>] \
  [--model-id <model>] \
  [--api-key <key>] \
  [--base-url <url>]
```

**Note:** AI analysis is always enabled. There is no `--use-ai` flag anymore.

## Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--input <path>` | Path to input assessment JSON file |
| `--output <path>` | Path to output enriched assessment JSON file |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--domain <domain>` | None | Domain for domain-specific enrichment (e.g., radiology, autonomous_vehicles) |
| `--config <path>` | `config/risk.toml` | Path to custom risk configuration TOML file |
| `--model-id <model>` | `deepseek-v4-flash` | AI model ID for insights generation |
| `--api-key <key>` | `ZEN_API_KEY` env var | API key for the AI model |
| `--base-url <url>` | `https://opencode.ai/zen/go/v1` | Base URL for the AI API |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ZEN_API_KEY` | API key for AI provider (used when `--api-key` not provided) |

## Usage Examples

### Basic Enrichment

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json
```

### With Domain-Specific Configuration

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology
```

### With Custom Configuration File

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology \
  --config /path/to/custom/risk.toml
```

### With Custom API Key

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology \
  --api-key your-api-key-here
```

### With Custom AI Endpoint

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology \
  --api-key your-api-key \
  --base-url https://custom-api.example.com/v1
```

### With Different AI Model

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain radiology \
  --model-id gpt-4o
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error (file not found, invalid JSON, AI error, etc.) |

## Input Format

The input `assessment.json` must contain:

```json
{
  "fmea_scores": [
    {
      "severity": 5,
      "occurrence": 3,
      "detectability": 4,
      "failure_mode": "Optional failure mode description"
    }
  ],
  "risk_register": {
    "records": [
      {
        "risk_id": "R-001",
        "title": "Risk title",
        "description": "Risk description",
        "severity": 5,
        "occurrence": 4,
        "detectability": 3,
        "strategy": "mitigate"
      }
    ]
  },
  "fairness_results": [...],
  "stress_results": [...]
}
```

## Output Format

The output `assessment_enriched.json` adds these AI-generated fields:

### FMEA Scores (AI-generated fields)

| Field | Description |
|-------|-------------|
| `root_cause_category` | Taxonomy category (e.g., "dataset_bias") |
| `root_cause` | Evidence-based analysis citing specific data points |
| `recommended_actions` | Actions from taxonomy, customized to failure |
| `mitigation_strategy` | EU AI Act Article 9 aligned strategy |
| `monitoring_recommendations` | Specific metrics, frequencies, acceptance criteria |
| `evidence_from_data` | Citations to assessment data used in analysis |
| `insights_source` | Always "ai" |
| `action_priority` | "high", "medium", "low", or "none" |
| `action_required` | Boolean flag |

### Risk Register (rule-based enrichment)

| Field | Description |
|-------|-------------|
| `residual_rpn` | RPN after applying controls |
| `mitigation_status` | "pending", "applied", or "verified" |

## Report Export

After enrichment, export reports:

```bash
# Export all formats
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --output-dir outputs/run_01/reports

# Export specific format
uv run python scripts/export_report.py \
  --input outputs/run_01/assessment_enriched.json \
  --format pdf \
  --output outputs/run_01/reports/report.pdf
```

## Related Documentation

- [Configuration Guide](./CONFIGURATION.md) - Configuration file details
- [Domain-Specific Configuration](./DOMAIN_CONFIGS.md) - How to set up domains
- [AI Integration](./AI_INTEGRATION.md) - AI provider configuration
- [Export System](./EXPORT_SYSTEM.md) - Report generation