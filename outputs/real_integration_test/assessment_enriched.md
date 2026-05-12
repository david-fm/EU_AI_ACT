# Compliance Assessment: nih-mobilenet-infiltration
- Framework: keras
- Run ID: run-2731e561d2f8
- Config hash: 571de72ba59cf575
- Run timestamp (UTC): 2026-04-14T17:20:16.416042+00:00
- Stress domain: generic
- Risk records: 4
- Report type: Enriched FMEA

## 1. Risk Register (Art. 9.2)
### R-FAIRNESS-GAP: Fairness disparity across metadata groups
- Severity: 5
- Occurrence: 4
- Detectability: 4
- RPN: 80
- Strategy: mitigate
- Mitigation status: applied
- Residual RPN: 72
- Current controls: Per-group fairness metrics
- Recommended action: Review sampling strategy and group-specific thresholds

### R-STRESS-XRAY_SENSOR_NOISE: Robustness degradation under xray_sensor_noise
- Severity: 1
- Occurrence: 2
- Detectability: 3
- RPN: 6
- Strategy: mitigate
- Mitigation status: applied
- Residual RPN: 10
- Current controls: Stress test taxonomy by domain
- Recommended action: Harden training with targeted augmentation

### R-STRESS-XRAY_SOFT_BLUR: Robustness degradation under xray_soft_blur
- Severity: 1
- Occurrence: 2
- Detectability: 4
- RPN: 8
- Strategy: mitigate
- Mitigation status: applied
- Residual RPN: 10
- Current controls: Stress test taxonomy by domain
- Recommended action: Harden training with targeted augmentation

### R-STRESS-XRAY_LOW_LIGHT: Robustness degradation under xray_low_light
- Severity: 1
- Occurrence: 2
- Detectability: 3
- RPN: 6
- Strategy: mitigate
- Mitigation status: applied
- Residual RPN: 10
- Current controls: Stress test taxonomy by domain
- Recommended action: Harden training with targeted augmentation

## 2. FMEA Analysis
### FMEA #1
- Failure Mode: Prediction quality drift under expected operating conditions
- S: 5 | O: 1 | D: 4 → RPN: 20
- Action Priority: low
- Action Required: No
- Root Cause: Distribution mismatch between observed and predicted outcomes
- Recommended Actions: Monitor performance metrics; Document known limitations; Schedule periodic reviews; Implement data drift monitoring
- Residual RPN: 15

## Stress Testing
### xray_sensor_noise (noise)
- Drop: -0.0052 | Max: -0.0026
- Entropy: 0.4885
### xray_soft_blur (blur)
- Drop: 0.0215 | Max: 0.0322
- Entropy: 0.5219
### xray_central_occlusion (occlusion)
- Drop: -0.0078 | Max: -0.0039
- Entropy: 0.3046
### xray_low_light (illumination)
- Drop: -0.0215 | Max: -0.0107
- Entropy: 0.4872
