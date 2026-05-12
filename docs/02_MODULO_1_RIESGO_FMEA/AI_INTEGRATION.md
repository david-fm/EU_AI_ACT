# AI Integration Guide - Risk FMEA Enrichment

This document explains how the AI-powered insights generation works.

## Overview

The module uses [Agno](https://agno.ai) agents to generate detailed FMEA insights using **full assessment context** (fairness metrics, stress results, risk register). AI analysis is **always enabled** - there is no fallback mode.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  ASSESSMENT DATA (Full Context)                 │
├─────────────────────────────────────────────────────────────────┤
│  fairness_results | stress_results | risk_register | taxonomy  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FMEAInsightGenerator                         │
├─────────────────────────────────────────────────────────────────┤
│  FMEAAIAgent (Agno Agent)                                       │
│  - OpenAILike model (deepseek-v4-flash, gpt-4o, etc.)           │
│  - Receives: failure mode + assessment data + domain taxonomy  │
│  - Returns: structured JSON with evidence-based insights       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT FIELDS                                │
├─────────────────────────────────────────────────────────────────┤
│  root_cause_category | root_cause_analysis                      │
│  recommended_actions | mitigation_strategy                      │
│  monitoring_recommendations | evidence_from_data                │
└─────────────────────────────────────────────────────────────────┘
```

## How AI Generation Works

### 1. Agent Initialization

```python
from agno.agent import Agent
from agno.models.openai import OpenAILike

agent = Agent(
    name="FMEA Risk Analyst",
    model=OpenAILike(
        id="deepseek-v4-flash",
        api_key=api_key,
        base_url="https://opencode.ai/zen/go/v1"
    ),
    instructions="You are an expert FMEA risk analyst specializing in AI systems...",
    markdown=False,
)
```

### 2. Prompt Construction with Full Context

The agent receives a structured prompt containing:

- **Failure Mode Details**: severity, occurrence, detectability, RPN, risk level
- **Domain Taxonomy**: root_cause_categories and action_types from config
- **Assessment Data**:
  - Fairness metrics (selection rates, TPR, FPR, equalized odds gaps by demographic)
  - Stress test results (perturbation name, performance drop, entropy)
  - Risk register (existing risks with controls)
  - Existing controls for this failure mode
- **Output Format**: Required JSON schema

### 3. Response Parsing

```python
# Extract JSON from response
json_start = response.content.find('{')
json_end = response.content.rfind('}') + 1
json_str = response.content[json_start:json_end]
data = json.loads(json_str)
```

### 4. Output Fields

The AI generates these fields:

| Field | Description |
|-------|-------------|
| `root_cause_category` | Taxonomy category (e.g., "dataset_bias", "image_quality") |
| `root_cause_analysis` | Evidence-based analysis citing specific data points |
| `recommended_actions` | List of actions from action taxonomy, customized to failure |
| `mitigation_strategy` | EU AI Act Article 9 aligned comprehensive strategy |
| `monitoring_recommendations` | Specific metrics, frequencies, acceptance criteria |
| `evidence_from_data` | Citations to assessment data that informed the analysis |

## Supported AI Providers

The module uses `OpenAILike` which supports any OpenAI-compatible API:

| Provider | Base URL | Configuration |
|----------|----------|---------------|
| ZEN (default) | `https://opencode.ai/zen/go/v1` | `ZEN_API_KEY` env var |
| OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` env var |
| DeepSeek | `https://api.deepseek.com/v1` | DeepSeek API key |
| Custom | Any OpenAI-compatible endpoint | Custom base URL |

## Configuration Options

### Environment Variables

```bash
# For ZEN API (default)
export ZEN_API_KEY=your-key-here

# For OpenAI
export OPENAI_API_KEY=sk-your-key-here
```

### CLI Arguments

```bash
# AI is always enabled (no --use-ai flag)
uv run python scripts/enriquecer_riesgo.py \
  --input assessment.json \
  --output assessment_enriched.json \
  --domain radiology \
  --model-id deepseek-v4-flash \
  --api-key your-key \
  --base-url https://custom-api.example.com/v1
```

### Programmatic Configuration

```python
from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher

config = FMEAConfig(domain="radiology")
enricher = FMEAEnricher(
    config=config,
    use_ai=True,
    model_id="deepseek-v4-flash",
    api_key="your-key",
    base_url="https://opencode.ai/zen/go/v1"
)
```

## Model Selection

### Recommended Models

| Model | Use Case | Strengths |
|-------|----------|-----------|
| `deepseek-v4-flash` | General FMEA analysis | Fast, cost-effective |
| `gpt-4o` | Complex domain analysis | High quality, broader context |
| `claude-sonnet` | Regulatory compliance | Excellent for EU AI Act analysis |

### Factors to Consider

1. **Quality vs Cost**: Larger models (GPT-4, Claude) produce better analysis but cost more
2. **Latency**: Flash models (deepseek-v4-flash) are faster for batch processing
3. **Context Window**: Larger models can handle more assessment data

## Prompt Engineering

The system prompt instructs the agent to:
1. Classify root cause into one taxonomy category
2. Analyze failure mode using actual assessment data
3. Cite specific data points in evidence (e.g., "senior TPR gap of 0.285")
4. Recommend actions from taxonomy, customized to the specific failure
5. Align mitigation strategy with EU AI Act Article 9

## Output Schema

The expected JSON output format:

```json
{
  "root_cause_category": "dataset_bias",
  "root_cause_analysis": "The failure mode is caused by dataset bias, evidenced by...",
  "recommended_actions": [
    "detect_and_prevent: Implement real-time monitoring...",
    "mitigate_and_control: Retrain with balanced dataset..."
  ],
  "mitigation_strategy": "Adopt comprehensive risk management aligned with EU AI Act Article 9...",
  "monitoring_recommendations": [
    "Metric: Selection rate by age group | Frequency: Daily | Acceptance: ratio >= 0.8"
  ],
  "evidence_from_data": [
    "TPR by age group: senior=0.326, young=0.611 (2x gap)",
    "Disparate impact ratio: 0.521 (below 0.8 threshold)"
  ]
}
```

## Error Handling

| Error Type | Behavior |
|------------|----------|
| Network timeout | Raises exception (no fallback) |
| Invalid API key | Raises exception (no fallback) |
| Invalid JSON response | Raises exception (no fallback) |
| Model unavailable | Raises exception (no fallback) |

**Note:** Unlike previous versions, there is no rule-based fallback. AI analysis is required for enriched FMEA generation.

## Performance Considerations

- AI generation adds latency (typically 2-10 seconds per FMEA score)
- Latency depends on amount of assessment data sent to AI
- Larger models with longer context windows may have higher latency

## Related Documentation

- [CLI Usage](./CLI_USAGE.md) - CLI arguments for enrichment
- [Domain-Specific Configuration](./DOMAIN_CONFIGS.md) - Domain taxonomies
- [Export System](./EXPORT_SYSTEM.md) - Report generation