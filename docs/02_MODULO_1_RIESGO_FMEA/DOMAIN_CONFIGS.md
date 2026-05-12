# Domain-Specific Configuration Guide

This document explains how to create and manage domain-specific configurations.

## What is Domain-Specific Configuration?

Domain-specific configuration provides:
- **Root Cause Taxonomy**: Categories for AI to classify root causes into (not prescriptive lists)
- **Action Taxonomy**: Action types for AI to select and customize based on failure mode
- **Failure Mode Templates**: Common failure modes with default controls

## Directory Structure

```
config/
├── risk.toml              # Default configuration (RPN thresholds, residual targets)
└── domains/
    ├── radiology.toml     # Radiology domain config
    ├── autonomous_vehicles.toml
    └── <new_domain>.toml  # Add new domains here
```

## Configuration Structure

### Default Config (`config/risk.toml`)

Contains RPN thresholds and residual risk targets - shared across all domains.

### Domain Config (`config/domains/<domain>.toml`)

Contains domain-specific taxonomy and failure mode templates.

## How to Create a Domain Configuration

### Step 1: Create the TOML file

Create `config/domains/<your_domain>.toml`

### Step 2: Define domain metadata

```toml
[fmea.domain_overrides]
domain = "your_domain_name"
```

### Step 3: Define failure mode templates (optional)

```toml
[fmea.failure_modes]
mode = "critical_failure_type"
cause = "Root cause description"
control = "Existing control description"
```

### Step 4: Define Root Cause Taxonomy

The taxonomy provides **categories** for the AI to classify root causes into. The AI generates specific analysis - it does NOT pick from a list.

```toml
[fmea.root_cause_taxonomy]
# Category name = Description for AI context
image_quality = "Issues related to image acquisition: exposure, positioning, artifacts, or modality-specific noise"
dataset_bias = "Issues related to training data: demographic imbalance, disease prevalence, equipment variability, annotation quality, or sampling bias"
model_limitations = "Issues related to model: architecture constraints, training data gaps, feature extraction, generalization to edge cases, or inference quirks"
workflow = "Issues related to human-AI interaction: fatigue, time pressure, context switching, trust calibration, or communication failures"
```

### Step 5: Define Action Taxonomy

The action taxonomy provides **action types** for the AI to select from and customize based on the specific failure.

```toml
[fmea.action_taxonomy]
# Action type = Description for AI context
detect_and_prevent = "Detect issues early and prevent harm through monitoring, alerts, or pre-emptive safeguards"
mitigate_and_control = "Reduce risk impact through architectural changes, procedural controls, or risk reduction measures"
document_and_inform = "Ensure transparency and traceability through documentation, logging, audit trails, and stakeholder disclosure"
monitor_and_review = "Ongoing monitoring through metrics tracking, periodic audits, performance reviews, and continuous assessment"
```

## Example: Radiology Domain

File: `config/domains/radiology.toml`

```toml
[fmea.domain_overrides]
domain = "radiology"

[fmea.failure_modes]
mode = "missed_pneumothorax"
cause = "Low contrast in pleural region due to underexposure or patient positioning"
control = "Dual-reader validation + confidence thresholding + quality checks"

[fmea.root_cause_taxonomy]
image_quality = "Issues related to image acquisition: exposure, positioning, artifacts, modality-specific noise, or reconstruction errors"
dataset_bias = "Issues related to training data: demographic imbalance, disease prevalence, equipment variability, annotation quality, or sampling bias"
model_limitations = "Issues related to model: architecture constraints, training data gaps, feature extraction, generalization to edge cases, or inference quirks"
workflow = "Issues related to human-AI interaction: fatigue, time pressure, context switching, trust calibration, or communication failures"

[fmea.action_taxonomy]
detect_and_prevent = "Detect issues early and prevent harm through monitoring, alerts, or pre-emptive safeguards"
mitigate_and_control = "Reduce risk impact through architectural changes, procedural controls, or risk reduction measures"
document_and_inform = "Ensure transparency and traceability through documentation, logging, audit trails, and stakeholder disclosure"
monitor_and_review = "Ongoing monitoring through metrics tracking, periodic audits, performance reviews, and continuous assessment"
```

## Example: Autonomous Vehicles

File: `config/domains/autonomous_vehicles.toml`

```toml
[fmea.domain_overrides]
domain = "autonomous_vehicles"

[fmea.failure_modes]
mode = "missed_pedestrian_at_night"
cause = "Insufficient training data for low-illumination pedestrian scenes"
control = "Night-vision augmentation pipeline + lidar fusion"

mode = "lane_drift"
cause = "Lane marker degradation or occlusion"
control = "HD map integration + camera fusion"

[fmea.root_cause_taxonomy]
sensor = "Issues related to sensors: degradation, calibration drift, environmental interference, or hardware failures"
perception = "Issues related to object detection: occlusion, adverse weather, edge cases, or classification errors"
planning = "Issues related to decision making: unusual scenarios, conflicting inputs, latency, or edge case handling"
infrastructure = "Issues related to external systems: V2X communication, map data staleness, or cloud service unavailability"

[fmea.action_taxonomy]
detect_and_prevent = "Detect issues early through sensor redundancy and monitoring to prevent hazardous situations"
mitigate_and_control = "Reduce impact through fail-safe mechanisms, ODD restrictions, and graceful degradation"
document_and_inform = "Ensure transparency through logging, incident reporting, and regulatory compliance documentation"
monitor_and_review = "Ongoing monitoring through fleet analytics, periodic validation, and continuous improvement"
```

## How to Add a New Domain

### 1. Research domain-specific failure modes

- Review industry standards (e.g., ISO 14971 for medical devices, ISO 26262 for automotive)
- Consult domain experts
- Analyze historical incident data

### 2. Define Root Cause Taxonomy

Identify 4-6 high-level categories that cover the main sources of failures in your domain.

### 3. Define Action Taxonomy

Identify 4-6 action types that cover the range of responses from detection to monitoring.

### 4. Create the domain TOML file

Follow the structure shown above with domain-specific values.

### 5. Test the configuration

```bash
uv run python scripts/enriquecer_riesgo.py \
  --input outputs/run_01/assessment.json \
  --output outputs/run_01/assessment_enriched.json \
  --domain your_new_domain
```

### 6. Verify enriched output

Check that:
- `root_cause_category` matches your taxonomy
- `recommended_actions` reference your action types
- AI analysis is evidence-based and domain-appropriate

## Taxonomy Design Principles

### Root Cause Categories Should Be:

1. **Mutually Exclusive**: Each failure maps to one category
2. **Domain-Appropriate**: Use domain terminology
3. **Specific**: Describe the type of issue, not a specific cause
4. **Comprehensive**: Cover all major failure sources

### Action Types Should Be:

1. **Distinct**: Each type addresses a different mitigation aspect
2. **Actionable**: Describe what to do, not just general guidance
3. **Sequential**: Cover the full lifecycle from detection to review
4. **Aligned with Regulations**: Consider EU AI Act Article 9 requirements

## Related Documentation

- [Configuration Guide](./CONFIGURATION.md) - Default configuration structure
- [CLI Usage](./CLI_USAGE.md) - How to use domain config with CLI
- [AI Integration](./AI_INTEGRATION.md) - AI insights generation details