# API Reference - Risk FMEA Enrichment Module

This document provides the Python API reference for the Risk and FMEA enrichment module.

## Module Import

```python
from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher, FMEAScore
from eu_ai_act.compliance.risk import RiskConfig, RiskEnricher, RiskRecord, RiskRegister
```

## FMEA Classes

### FMEAScore

```python
@dataclass(frozen=True, slots=True)
class FMEAScore:
    severity: int
    occurrence: int
    detectability: int
    failure_mode: str | None = None
    root_cause: str | None = None
    current_controls: str | None = None
    recommended_actions: str | None = None
    residual_rpn: int | None = None
    action_required: bool = False
    action_priority: str | None = None
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `rpn` | `int` | Risk Priority Number (severity × occurrence × detectability) |
| `high_risk` | `bool` | True if RPN >= 100 |

#### Methods

##### `to_dict() -> dict[str, Any]`

Returns a dictionary representation of the FMEA score.

```python
score = FMEAScore(severity=5, occurrence=4, detectability=3)
data = score.to_dict()
# {'severity': 5, 'occurrence': 4, 'detectability': 3, 'rpn': 60, ...}
```

---

### FMEAConfig

```python
class FMEAConfig:
    def __init__(self, config_path: Path | None = None, domain: str | None = None)
```

Loads and manages FMEA configuration from TOML files.

#### Constructor Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `config_path` | `Path \| None` | `Path("config/risk.toml")` | Path to config file |
| `domain` | `str \| None` | `None` | Domain name for domain-specific config |

#### Methods

##### `get_threshold(level: str) -> int`

Get RPN threshold for action priority level.

```python
config = FMEAConfig()
high_threshold = config.get_threshold("high")  # 120
medium_threshold = config.get_threshold("medium")  # 60
```

##### `get_root_causes() -> dict[str, list[str]]`

Get domain-specific root causes.

```python
config = FMEAConfig(domain="radiology")
root_causes = config.get_root_causes()
# {'image_quality': [...], 'dataset_bias': [...], ...}
```

##### `get_recommended_actions(rpn: int) -> list[str]`

Get recommended actions based on RPN.

```python
config = FMEAConfig(domain="radiology")
actions = config.get_recommended_actions(150)
# ['Implement dual-reader workflow', ...]
```

##### `get_failure_mode_config() -> dict[str, str]`

Get domain-specific failure mode configuration.

---

### FMEAEnricher

```python
class FMEAEnricher:
    def __init__(
        self,
        config: FMEAConfig,
        use_ai: bool = False,
        model_id: str = "deepseek-v4-flash",
        api_key: str | None = None,
        base_url: str = "https://opencode.ai/zen/go/v1"
    )
```

Enriches FMEA scores with domain-specific information and AI insights.

#### Constructor Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `config` | `FMEAConfig` | (required) | Configuration object |
| `use_ai` | `bool` | `False` | Enable AI-powered insights |
| `model_id` | `str` | `"deepseek-v4-flash"` | AI model identifier |
| `api_key` | `str \| None` | `None` | AI API key |
| `base_url` | `str` | ZEN endpoint | AI API base URL |

#### Methods

##### `enrich_score(score: FMEAScore) -> FMEAScore`

Enrich a single FMEA score (rule-based).

```python
config = FMEAConfig(domain="radiology")
enricher = FMEAEnricher(config)
score = FMEAScore(severity=8, occurrence=6, detectability=7)
enriched = enricher.enrich_score(score)
```

##### `enrich_scores(scores: list[FMEAScore]) -> list[FMEAScore]`

Enrich multiple FMEA scores (rule-based).

```python
scores = [FMEAScore(severity=5, occurrence=4, detectability=3), ...]
enriched = enricher.enrich_scores(scores)
```

##### `enrich_score_with_ai(score: FMEAScore) -> FMEAScore`

Enrich a single FMEA score with AI insights (async).

```python
config = FMEAConfig(domain="radiology")
enricher = FMEAEnricher(config, use_ai=True)
score = FMEAScore(severity=8, occurrence=6, detectability=7)
enriched = await enricher.enrich_score_with_ai(score)
```

##### `enrich_scores_with_ai(scores: list[FMEAScore]) -> list[FMEAScore]`

Enrich multiple FMEA scores with AI insights (async).

```python
enriched = await enricher.enrich_scores_with_ai(scores)
```

---

## Risk Classes

### RiskRecord

```python
@dataclass(slots=True)
class RiskRecord:
    risk_id: str
    title: str
    description: str
    severity: int
    occurrence: int
    detectability: int
    strategy: RiskStrategy  # "eliminate" | "mitigate" | "inform"
    cause: str | None = None
    current_controls: str | None = None
    recommended_action: str | None = None
    residual_rpn: int | None = None
    mitigation_status: MitigationStatus = "pending"  # "pending" | "applied" | "verified"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `rpn` | `int` | Risk Priority Number |
| `high_risk` | `bool` | True if RPN >= 40 |

#### Methods

##### `to_dict() -> dict[str, object]`

Returns a dictionary representation of the risk record.

---

### RiskRegister

```python
@dataclass(slots=True)
class RiskRegister:
    records: list[RiskRecord] = field(default_factory=list)
```

A collection of risk records.

#### Methods

##### `add(record: RiskRecord) -> None`

Add a risk record to the register.

```python
register = RiskRegister()
register.add(RiskRecord(risk_id="R-001", ...))
```

##### `to_dict() -> dict[str, object]`

Returns a dictionary representation with `"records"` and `"total_records"`.

---

### RiskConfig

```python
class RiskConfig:
    def __init__(self, config_path: Path | None = None, domain: str | None = None)
```

Loads and manages risk configuration from TOML files.

#### Methods

##### `get_rpn_thresholds() -> dict[str, int]`

Get RPN thresholds from configuration.

```python
config = RiskConfig()
thresholds = config.get_rpn_thresholds()
# {'high': 120, 'medium': 60, 'low': 20}
```

##### `get_residual_targets() -> dict[str, int]`

Get residual RPN targets from configuration.

```python
targets = config.get_residual_targets()
# {'high': 80, 'medium': 40, 'low': 10}
```

---

### RiskEnricher

```python
class RiskEnricher:
    def __init__(self, config: RiskConfig)
```

Enriches risk records with residual RPN and mitigation status.

#### Methods

##### `enrich_record(record: RiskRecord) -> RiskRecord`

Enrich a single risk record.

```python
config = RiskConfig()
enricher = RiskEnricher(config)
record = RiskRecord(risk_id="R-001", ...)
enriched = enricher.enrich_record(record)
```

##### `enrich_register(register: RiskRegister) -> RiskRegister`

Enrich all records in a risk register.

```python
enriched_register = enricher.enrich_register(register)
```

---

## Usage Examples

### Basic Enrichment (Rule-Based)

```python
from pathlib import Path
from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher, FMEAScore
from eu_ai_act.compliance.risk import RiskConfig, RiskEnricher, RiskRecord, RiskRegister

# Create config
config = FMEAConfig(domain="radiology")
enricher = FMEAEnricher(config)

# Enrich FMEA scores
scores = [FMEAScore(severity=8, occurrence=6, detectability=7)]
enriched_scores = enricher.enrich_scores(scores)

# Enrich risk register
risk_config = RiskConfig()
risk_enricher = RiskEnricher(risk_config)
register = RiskRegister()
register.add(RiskRecord(
    risk_id="R-001",
    title="Test Risk",
    severity=5,
    occurrence=4,
    detectability=3,
    strategy="mitigate",
    current_controls="Dual-reader validation"
))
enriched_register = risk_enricher.enrich_register(register)
```

### With AI-Powered Insights

```python
import asyncio
from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher, FMEAScore

async def enrich_with_ai():
    config = FMEAConfig(domain="radiology")
    enricher = FMEAEnricher(
        config,
        use_ai=True,
        model_id="deepseek-v4-flash",
        api_key="your-api-key",
        base_url="https://opencode.ai/zen/go/v1"
    )

    scores = [FMEAScore(severity=8, occurrence=6, detectability=7)]
    enriched_scores = await enricher.enrich_scores_with_ai(scores)

    return enriched_scores

enriched = asyncio.run(enrich_with_ai())
```

### Processing Assessment JSON

```python
import json
from pathlib import Path
from eu_ai_act.compliance.fmea import FMEAConfig, FMEAEnricher
from eu_ai_act.compliance.risk import RiskConfig, RiskEnricher

def enrich_assessment(assessment: dict, domain: str | None = None) -> dict:
    fmea_config = FMEAConfig(domain=domain)
    fmea_enricher = FMEAEnricher(fmea_config)

    risk_config = RiskConfig(domain=domain)
    risk_enricher = RiskEnricher(risk_config)

    # Process FMEA scores
    if "fmea_scores" in assessment:
        scores = [FMEAScore(**s) for s in assessment["fmea_scores"]]
        enriched_scores = fmea_enricher.enrich_scores(scores)
        assessment["fmea_scores"] = [s.to_dict() for s in enriched_scores]

    # Process risk register
    if "risk_register" in assessment:
        register = RiskRegister()
        for record in assessment["risk_register"]["records"]:
            register.add(RiskRecord(**record))
        enriched_register = risk_enricher.enrich_register(register)
        assessment["risk_register"] = enriched_register.to_dict()

    return assessment

# Load and process
with open("assessment.json") as f:
    assessment = json.load(f)

enriched = enrich_assessment(assessment, domain="radiology")

with open("assessment_enriched.json", "w") as f:
    json.dump(enriched, f, indent=2)
```

## Related Documentation

- [Configuration Guide](./CONFIGURATION.md) - Configuration file format
- [Domain-Specific Configuration](./DOMAIN_CONFIGS.md) - Domain setup
- [CLI Usage](./CLI_USAGE.md) - CLI reference
- [AI Integration](./AI_INTEGRATION.md) - AI configuration details