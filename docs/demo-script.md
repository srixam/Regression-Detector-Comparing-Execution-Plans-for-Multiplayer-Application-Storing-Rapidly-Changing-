# QueryGuard: 3-Minute Live Demonstration Script

This script outlines the exact 3-minute stakeholder presentation and live execution flow for demonstrating QueryGuard.

---

### Timeline Overview
- **0:00 – 0:25**: The Problem & Multiplayer Challenge
- **0:25 – 0:45**: Architecture & Hybrid Signal Formulation
- **0:45 – 1:10**: Healthy Baseline Demonstration
- **1:10 – 1:40**: Index-Removal Regression Trigger
- **1:40 – 2:00**: CRITICAL Alert & Evidence Inspection
- **2:00 – 2:20**: Plan Comparison & Root-Cause Attribution
- **2:20 – 2:40**: Reliability Fault Injection (Duplicates, Delays, Out-of-Order)
- **2:40 – 3:00**: Empirical Scorecard & Early Warning Before User Impact

---

## Step-by-Step Script

### [0:00 – 0:25] The Problem
- **Narrator**:
  > "In multiplayer games managing volatile player state, queries frequently suffer unpredictable regressions. Traditional APM monitoring triggers alerts when p95 spikes, but leaves engineers asking: Did the execution plan change? Was an index dropped? Are table statistics stale? Or is this just a traffic surge? Today, we demonstrate QueryGuard, an explainable query-regression detector that answers these questions before users are impacted."

### [0:25 – 0:45] Architecture
- **Action**: Show **Overview** page (`http://localhost:8501`).
- **Narrator**:
  > "QueryGuard ingests telemetry across query executions, PostgreSQL execution plans, index metadata, catalog statistics, and release histories. It processes events through a deduplication and chronological ordering pipeline before evaluating a 5-dimension hybrid score."

### [0:45 – 1:10] Healthy Baseline
- **Action**: Navigate to **7_Simulation** and click **"Run Healthy Baseline"**.
- **Narrator**:
  > "We establish a clean baseline across our 7 representative multiplayer queries. Notice all queries are executing via Index Scans with p95 latencies around 24 milliseconds and zero active alerts."

### [1:10 – 1:40] Trigger Index Removal Regression
- **Action**: Click **"Index Removal Regression"**.
- **Narrator**:
  > "Now, simulating a zero-downtime deployment where the index `idx_player_session` was inadvertently removed, QueryGuard ingests the new workload."

### [1:40 – 2:00] Inspect CRITICAL Alert
- **Action**: Navigate to **2_Regression_Alerts**.
- **Narrator**:
  > "Immediately, QueryGuard flags a CRITICAL alert. The regression score is 94.5 out of 100. Latency surged by +680% to 191 milliseconds, and the detector reports 96% confidence."

### [2:00 – 2:20] Plan Comparison & Root Cause
- **Action**: Open **3_Query_Investigation** and view the plan diff.
- **Narrator**:
  > "QueryGuard explains why: the execution plan collapsed from an `Index Scan` on `idx_player_session` to a catastrophic `Seq Scan` on `game_sessions`. Cost jumped from 8.30 to 485.00, and shared read disk blocks rose from 0 to 45. QueryGuard correlates this with release `v2.3.1` deployed 11 minutes prior, diagnosing the root cause as a missing index after schema deployment."

### [2:20 – 2:40] Reliability & Fault Injection
- **Action**: Open **7_Simulation** and click **"Duplicate Events"** and **"Out-of-Order Events"**.
- **Narrator**:
  > "In multiplayer telemetry, network jitter causes duplicates and out-of-order deliveries. QueryGuard's normalizer drops 100% of duplicates with zero state corruption and re-sequences events chronologically by event_time."

### [2:40 – 3:00] Scorecard & Early Warning Before User Impact
- **Action**: Navigate to **8_Evaluation**.
- **Narrator**:
  > "Looking at our empirical scorecard, QueryGuard achieves 100% Recall, 94.7% Precision, and 0 False Negatives across benchmark trials. Most critically, our controlled early warning experiment demonstrates detection **78 seconds before simulated user gameplay impact**, proving that regressions are caught before players experience lag. Thank you!"
