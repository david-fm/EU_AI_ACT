# Configuration Guide - Risk and FMEA Enrichment

This document explains how to configure the Risk and FMEA enrichment module.

## Configuration File Location

Default path: `config/risk.toml`

Custom path can be provided via `--config` CLI argument.

## TOML Structure

### FMEA Thresholds

```toml
[fmea]
# RPN thresholds for action priority
high_rpn_threshold = 120    # RPN >= 120 → "high" priority
medium_rpn_threshold = 60    # RPN >= 60 → "medium" priority
low_rpn_threshold = 20       # RPN >= 20 → "low" priority

# Residual risk reduction targets
residual_rpn_target_high = 80    # Target residual for high RPN
residual_rpn_target_medium = 40  # Target residual for medium RPN
residual_rpn_target_low = 10     # Target residual for low RPN
```

### Action Priority Mapping

```toml
[fmea.action_priority]
high = { min_rpn = 120, description = "Immediate action required" }
medium = { min_rpn = 60, description = "Action recommended within 30 days" }
low = { min_rpn = 20, description = "Monitor and review periodically" }
none = { min_rpn = 0, description = "Acceptable risk" }
```

## How to Modify Thresholds

### Example: Stricter Risk Tolerance

If your organization requires stricter risk control:

```toml
[fmea]
high_rpn_threshold = 80    # Lower threshold for high priority
medium_rpn_threshold = 40
low_rpn_threshold = 15

residual_rpn_target_high = 50
residual_rpn_target_medium = 25
residual_rpn_target_low = 5
```

### Example: More Lenient Risk Tolerance

```toml
[fmea]
high_rpn_threshold = 150   # Higher threshold for high priority
medium_rpn_threshold = 80
low_rpn_threshold = 30

residual_rpn_target_high = 100
residual_rpn_target_medium = 60
residual_rpn_target_low = 15
```

## Configuration Loading

The configuration is loaded in this order:

1. **Default config** (`config/risk.toml`) is always loaded first
2. **Domain-specific config** (`config/domains/<domain>.toml`) is loaded if `--domain` is specified
3. **Domain config overrides** the default config for matching keys

### Example Loading Behavior

```
Default config (config/risk.toml):
  - high_rpn_threshold = 120

Domain config (config/domains/radiology.toml):
  - high_rpn_threshold = 100 (this overrides the default)

Final value used: 100
```

## Validation

The module does not perform schema validation on TOML files. Ensure:
- All threshold values are integers
- RPN thresholds follow: high >= medium >= low
- Residual targets follow: high >= medium >= low

## Environment Variables

The following environment variables are used:

| Variable | Description |
|----------|-------------|
| `ZEN_API_KEY` | API key for AI provider (can also be set via `--api-key`) |

## Related Documentation

- [Domain-Specific Configuration](./DOMAIN_CONFIGS.md) - How to create domain configs
- [CLI Usage](./CLI_USAGE.md) - How to use the CLI with custom configs
- [AI Integration](./AI_INTEGRATION.md) - AI configuration details