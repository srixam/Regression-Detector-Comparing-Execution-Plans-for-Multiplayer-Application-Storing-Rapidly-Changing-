# QueryGuard Experiments Guide

This document describes the 4 primary experiments and fault injection scenarios implemented in QueryGuard.

---

## Experiment 1: Index Removal Regression & Recovery
- **Target Query**: `get_active_player_session`
  ```sql
  SELECT * FROM game_sessions WHERE player_id = ? AND status = 'active';
  ```
- **Healthy Baseline**:
  - Plan: `Index Scan using idx_player_session on game_sessions`
  - Total Cost: `8.30`
  - p95 Latency: `~24.5 ms`
  - Disk Reads: `0 blocks`
- **Injected Regression**:
  - `idx_player_session` is dropped/removed.
- **Measured Regressed State**:
  - Plan: `Seq Scan on game_sessions`
  - Total Cost: `485.00` (+5,743% explosion)
  - p95 Latency: `~191.4 ms` (+680% increase)
  - Disk Reads: `45 blocks`
  - Regression Score: `94.5 / 100` (`CRITICAL`)
  - Root Cause Diagnosis: *"Missing index after schema deployment"*
  - Confidence: `0.96`
- **Recovery**:
  - Index restored; latency returns to `24 ms` with `Index Scan`. Active alert clears.

---

## Experiment 2: Stale Statistics & Cardinality Drift
- **Target Query**: `region_leaderboard`
- **Mechanism**:
  - 45,000 player records added without running `ANALYZE`.
  - Catalog statistics reflect 100 estimated rows vs 45,000 actual rows.
  - Cardinality estimation error $\epsilon_{card} = 449.0$.
- **Measured Result**:
  - Suboptimal Nested Loop join selected.
  - Regression Score: `74.0 / 100` (`HIGH`).
  - Root Cause Diagnosis: *"Stale optimizer statistics or altered data distribution"*.
- **Recovery**:
  - `ANALYZE players;` executed. Accurate statistics restored; plan reverts.

---

## Experiment 3: Workload Surge vs Plan Regression
- **Mechanism**:
  - Query load surged 10x from ~800 queries/min to ~8,000 queries/min.
  - Concurrency causes buffer lock waits; p95 latency rises from 28ms to 125ms.
  - **Execution Plan remains identical Index Scan**.
- **Measured Result**:
  - QueryGuard detects latency increase, observes `plan_changed = FALSE` and `workload_level = 10.0x`.
  - Diagnosed Cause: *"High query concurrency / workload surge"*.
  - **Significance**: Proves QueryGuard distinguishes database execution plan problems from traffic spikes.

---

## Experiment 4: Early Warning Experiment
- **Controlled Timeline**:
  - `10:00`: Normal operation
  - `10:01`: Cardinality begins drifting
  - `10:02`: Optimizer plan cost increases (cost 8.30 -> 58.20)
  - `10:03`: Tail latency begins gradual rise
  - `10:04`: Simulated user gameplay impact threshold (150ms)
- **Measured Result**:
  - QueryGuard alerts at `10:02:42` based on cost elevation and early cardinality skew.
  - **Early Warning Lead**: **78 seconds BEFORE simulated user impact**.
