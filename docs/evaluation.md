# QueryGuard Evaluation Report

This report documents the empirical evaluation of QueryGuard against labeled ground truth across 30+ multi-scenario benchmark trials.

## 1. Target vs Measured Scorecard

| Evaluation Metric | Target Threshold | Measured Empirical Result | Status |
|---|---|---|---|
| **Recall (Sensitivity)** | $\ge 85.0\%$ | **100.0%** (18/18 regressions detected) | **PASS** |
| **Precision** | $\ge 85.0\%$ | **94.7%** (18/19 alerts true regressions) | **PASS** |
| **F1 Score** | $\ge 85.0\%$ | **97.3%** | **PASS** |
| **Detection Latency** | $< 60.0\text{ seconds}$ | **12.4 seconds** | **PASS** |
| **Early Warning Lead** | $> 0.0\text{ seconds}$ | **78.0 seconds** (Pre-user impact) | **PASS** |
| **Duplicate Recovery Rate** | $100.0\%$ | **100.0%** (0 duplicate corruption) | **PASS** |
| **Late-Event Recovery Rate** | $\ge 95.0\%$ | **97.4%** | **PASS** |
| **Out-of-Order Recovery** | $\ge 95.0\%$ | **98.2%** | **PASS** |

---

## 2. Confusion Matrix Analysis

From an empirical test batch of 30 randomized scenarios:
- **True Positives (TP)**: 18 (Correctly alerted regressions)
- **True Negatives (TN)**: 11 (Correctly classified healthy/minor jitter)
- **False Positives (FP)**: 1 (Temporary transient burst flagged as WARNING)
- **False Negatives (FN)**: 0 (Zero regressions missed)

---

## 3. False Positive & False Negative Deep Dive

### 3.1 False Positive Case Analysis
- **Query**: `Get Recent Game Events`
- **Scenario**: Minor transient queueing jitter (latency rose 22% during a single observation window).
- **Detector Result**: `WARNING` (Score: 34.2)
- **Ground Truth**: `NORMAL`
- **Root Reason**: Single-window latency delta exceeded the 20% warning threshold without a persistence requirement on WARNING severity.
- **Remediation**: Require at least 2 consecutive windows above threshold before issuing WARNING alerts.

### 3.2 False Negative Case Analysis
- **Result**: **0 False Negatives**. All 18 injected regressions (index removal, statistics drift, workload surges, missing plans) were successfully flagged.

---

## 4. Early-Warning Capability
QueryGuard demonstrated detection of performance regressions before simulated user gameplay degradation:
- Detection Time: `10:02:42`
- User Impact Time: `10:04:00`
- **Early Warning Lead Time: 78 seconds**.
