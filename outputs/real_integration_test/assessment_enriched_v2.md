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
- Failure Mode: Prediction quality drift under expected operating conditions [AI]
- S: 5 | O: 1 | D: 4 → RPN: 20
- Action Priority: low
- Action Required: No
- Root Cause Category: dataset_bias
- Root Cause Analysis: The failure mode 'Prediction quality drift under expected operating conditions' is primarily caused by dataset bias, as evidenced by the fairness metrics showing systematic disparities across demographic groups. The age group analysis reveals severe imbalances: the selection rate for seniors is 0.289 versus 0.554 for young, a 1.9× ratio. True positive rates show an even larger gap (senior 0.326 vs young 0.611), and the false positive rate for young (0.5) is almost double that for seniors (0.270). The equalized odds gap across age groups is 0.285, and the disparate impact ratio is only 0.521, indicating that the model performs unequally across age cohorts. For gender, while smaller, the equalized odds gap is 0.059 and the disparate impact ratio (0.971 at cohort level) suggests some imbalance. These patterns likely stem from under‑representation of senior subjects in the training data and possible differences in image characteristics (e.g., lower bone density, different positioning) that the model did not learn to handle robustly. Stress test perturbations are relatively mild, confirming that systematic demographic bias is the dominant root cause.
- Recommended Actions: detect_and_prevent: Implement real-time monitoring of prediction quality across age groups, with automatic alerts when selection rate or TPR gaps exceed predefined thresholds (e.g., disparate impact ratio < 0.8).; mitigate_and_control: Retrain the model using a stratified dataset with balanced representation across all age groups and genders, applying techniques such as re‑weighting or synthetic augmentation (e.g., StyleGAN‑based generation of senior X‑rays).; document_and_inform: Update the AI system log and transparency documentation (EU AI Act Art. 13) to include per‑demographic performance metrics, planned bias mitigation steps, and clear limitations regarding performance on underrepresented groups.; monitor_and_review: Conduct quarterly fairness audits (e.g., equalized odds, demographic parity) and stress tests with demographic‑specific perturbations. Review results with a human oversight committee and adjust model or thresholds accordingly.
- Mitigation Strategy: Adopt a comprehensive risk management approach aligned with EU AI Act Article 9: (1) Identify risks: systematic fairness evaluation highlighted demographic disparities as high‑risk (R‑FAIRNESS‑GAP RPN=80). (2) Implement bias mitigation: collect more representative data, apply fairness‑aware training (e.g., adversarial debiasing), and set per‑group optimal thresholds (note current optimal thresholds differ: young/adult 0.2 vs senior 0.4, suggesting the model is less confident for seniors). (3) Deploy multi‑level monitoring: online tracking of prediction quality by age/gender, with automated fallback to a simpler model if severe drift is detected. (4) Establish a closed‑loop feedback system: clinical users report misclassifications, which are used for periodic fine‑tuning. (5) Document all mitigation measures and validation results to support conformity assessment under the AI Act Annex IV. The goal is to reduce demographic performance gaps and ensure the system maintains acceptable prediction quality across all expected operational demographics.
- Monitoring Recommendations: Metric: Selection rate, TPR, FPR and equalized odds gap by age group and gender. Frequency: Daily for selection rate, weekly for TPR/FPR on live data. Acceptance criteria: Disparate impact ratio ≥ 0.8 (per US EEOC guidelines) and equalized odds gap ≤ 0.1.; Metric: Prediction quality drift index (e.g., PSI or distribution of confidence scores) per demographic. Frequency: Weekly. Acceptance criteria: Drift index within ±0.05 of baseline for all groups.; Metric: Model Brier score and ECE by demographic. Frequency: Monthly. Acceptance criteria: No group should have ECE > 0.25 or Brier score > 0.3.; Review frequency: Monthly risk review meeting (including domain experts) to examine fairness dashboards and decide on retraining triggers.
- Evidence from Data: Selection rate by age group: young=0.554, adult=0.396, senior=0.289 (2× gap between senior and young)., True positive rate by age group: young=0.611, adult=0.492, senior=0.326 (senior TPR is half of young)., False positive rate by age group: young=0.500, adult=0.335, senior=0.270 (young have significantly higher FPR)., Equalized odds gap by age group: 0.285 (ten times the gender gap of 0.059), indicating severe age‑related unfairness., Disparate impact ratio by age group: 0.521, well below the commonly accepted 0.8 threshold for adverse impact., Optimal thresholds differ by gender: M=0.2, F=0.4, showing the model's decision strategy varies by gender., Risk register: R‑FAIRNESS‑GAP rated RPN=80 (high), currently only controlled by per‑group fairness metrics (insufficient)., Stress test degradation is low (max drop 0.021 for soft blur), implying perturbations are not the primary drift driver.
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
