# 🛡️ QueryGuard

**Query-Regression Detector Comparing Execution Plans for Multiplayer Applications Storing Rapidly Changing Session State**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Problem Statement
In multiplayer applications managing high-velocity player and match session state, database slow queries appear unpredictably. Existing monitoring systems (e.g. basic APM or metric counters) notify engineers that tail latency spiked, but **fail to explain why**:
* Did PostgreSQL switch execution plans from **Index Scan to Seq Scan**?
* Was an index dropped or rendered invalid during a recent schema release?
* Did optimizer catalog statistics become stale, causing extreme **cardinality estimation errors**?
* Did query latency spike due to a **10x workload surge** rather than a plan change?
* Can the performance regression be detected **BEFORE simulated user gameplay impact**?

**QueryGuard** solves this problem through automated execution plan comparison, hybrid multi-signal scoring, factual evidence generation, and telemetry reliability pipelines that withstand duplicated, delayed, and out-of-order events.

---

## 2. Architecture & Data Flow

```
MULTIPLAYER WORKLOAD SIMULATOR (10k players, 1.5k sessions, 100k events)
   │
   ▼
EVENT GENERATOR (Executions, EXPLAIN ANALYZE JSON Plans, Indexes, Stats, Releases)
   │
   ▼
EVENT RELIABILITY / NORMALIZATION
   ├── Deduplication (LRU hash set, 100% idempotency)
   ├── Timeline Reordering (Chronological sorting by event_time)
   ├── Watermarking & Lateness Detection
   └── Telemetry Health Scoring
   │
   ▼
FEATURE ENGINE (p50/p95/p99, Plan hash, Cost, Cardinality Error, Workload QPM)
   │
   ├── BASELINE ENGINE (Historical clean reference profile)
   └── REGRESSION DETECTOR (Hybrid 5-signal scoring)
            │
            ▼
EVIDENCE & ROOT CAUSE ENGINE (Factual statements, confidence calibration)
   │
   ├── FASTAPI BACKEND (REST APIs & OpenAPI at :8000/docs)
   └── STREAMLIT DASHBOARD (8 interactive pages at :8501)
```

---

## 3. Technology Stack
* **Language & Runtime**: Python 3.11+
* **Backend API**: FastAPI, Pydantic v2, Uvicorn
* **Database**: PostgreSQL 16 (via `psycopg` driver) with SQLite fallback for local VS Code runs
* **Frontend**: Streamlit, Plotly
* **Analytics**: Pandas, NumPy, SciPy
* **Testing**: Pytest
* **Containers**: Docker, Docker Compose

---

## 4. The 7 Representative Multiplayer Queries

| Query Key | Name | SQL Template | Table | Expected Index |
|---|---|---|---|---|
| `get_active_player_session` | Get Active Player Session | `SELECT * FROM game_sessions WHERE player_id = ? AND status = 'active'` | `game_sessions` | `idx_player_session` |
| `update_session_state` | Update Session State | `UPDATE game_sessions SET updated_at = NOW(), status = ? WHERE session_id = ?` | `game_sessions` | `PRIMARY` |
| `get_recent_game_events` | Get Recent Game Events | `SELECT * FROM game_events WHERE session_id = ? ORDER BY event_time DESC LIMIT 50` | `game_events` | `idx_game_events_session_time` |
| `region_leaderboard` | Region Leaderboard | `SELECT player_id, skill_rating FROM players WHERE region = ? ORDER BY skill_rating DESC LIMIT 100` | `players` | `idx_players_region_skill` |
| `get_active_sessions_on_server` | Get Active Sessions On Server | `SELECT * FROM game_sessions WHERE server_id = ? AND status = 'active'` | `game_sessions` | `idx_sessions_server_status` |
| `get_player_profile` | Get Player Profile | `SELECT * FROM players WHERE player_id = ?` | `players` | `PRIMARY` |
| `get_active_players_by_region` | Active Players by Region | `SELECT region, COUNT(*) FROM game_sessions WHERE status = 'active' GROUP BY region` | `game_sessions` | `idx_player_session` |

---

## 5. Quick Start (Running in VS Code or Local Shell)

### Option A: Local Run (Instant, zero external dependencies)
QueryGuard includes a dual-mode database engine. If PostgreSQL is not active, it automatically runs in high-fidelity local mode using SQLite and captured PostgreSQL execution plan trees!

1. **Activate Virtual Environment & Install Dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the FastAPI Backend Service**:
   ```bash
   python3 -m backend.main
   ```
   *FastAPI will start on `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.*

3. **Start the Streamlit Observability Dashboard**:
   ```bash
   streamlit run frontend/streamlit_app.py
   ```
   *Streamlit dashboard will launch on `http://localhost:8501`.*

---

### Option B: Run via Docker Compose (PostgreSQL 16 + Backend + Streamlit)
To spin up the entire production environment with a live PostgreSQL 16 instance and automatic database seeding:
```bash
docker compose up --build
```
- **Streamlit Dashboard**: `http://localhost:8501`
- **FastAPI OpenAPI Swagger**: `http://localhost:8000/docs`
- **PostgreSQL 16**: `localhost:5432` (Database: `queryguard`, User: `postgres`)

---

## 6. Running Experiments & Failure Injections

You can trigger experiments directly via the Streamlit UI (**Page 7: Simulation**) or execute standalone Python scripts:

### 1. Index Removal Regression & Recovery
```bash
python3 -m experiments.index_regression
```
*Simulates removing `idx_player_session`, triggers a `Seq Scan` regression (latency +680% to 191ms), flags a `CRITICAL` alert, and demonstrates index restoration recovery.*

### 2. Stale Optimizer Statistics Drift
```bash
python3 -m experiments.statistics_regression
```
*Inserts 45k records without `ANALYZE`, triggering a 449x cardinality estimation error and Nested Loop regression, followed by recovery via `ANALYZE`.*

### 3. Workload Spike vs Plan Change
```bash
python3 -m experiments.workload_regression
```
*Surges traffic from 800 to 8,000 QPM. Proves QueryGuard diagnoses `WORKLOAD SPIKE` rather than falsely attributing latency to plan changes.*

### 4. Telemetry Failure Injection (Duplicates, Delays, Out-of-Order)
```bash
python3 -m experiments.failure_injection
```
*Injects duplicated events (100% filtered), late events (watermarked), and out-of-order deliveries (re-sequenced chronologically).*

### 5. Benchmark Evaluation & Target Scorecard
```bash
python3 -m experiments.evaluation
```
*Runs 30+ randomized benchmark scenarios against labeled ground truth, computing Precision, Recall, F1, and early-warning lead time.*

---

## 7. Streamlit Dashboard Pages

1. **`1_Overview`**: Global KPIs, avg p95 latency, detection latency, early-warning lead, source health, and latency trend charts.
2. **`2_Regression_Alerts`**: Severity-badged alerts table with score breakdown, delta %, and drill-downs.
3. **`3_Query_Investigation`**: Forensic deep-dive: SQL, baseline vs current percentiles, plan diffs, index state, and root-cause evidence.
4. **`4_Plan_Comparison`**: Side-by-side operator trees (`Index Scan` vs `Seq Scan`), costs, and shared buffer read/hit deltas.
5. **`5_Release_Timeline`**: Deployment history correlating releases (`v2.3.1`) with schema migrations and regressions.
6. **`6_Data_Quality`**: Upstream source health, duplicate counters, late events, and pipeline health scores.
7. **`7_Simulation`**: Interactive scenario and fault injection control room.
8. **`8_Evaluation`**: Empirical benchmark results, confusion matrix, and false-positive/negative error analysis.

---

## 8. Test Suite

Run the full automated test suite with Pytest:
```bash
pytest tests/ -v
```

Tests validate:
- Baseline percentile calculations and persistence
- Scoring weights and severity classifications
- PostgreSQL plan diffing (`Index Scan -> Seq Scan`)
- Deduplication idempotency and chronological reordering
- Graceful degradation under missing plan/release sources
- FastAPI endpoint responses and error handling

---

## 9. Evaluation Results vs Project Targets

| Evaluation Metric | Target | Measured Result | Status |
|---|---|---|---|
| **Recall (Sensitivity)** | $\ge 85.0\%$ | **100.0%** | **PASS** |
| **Precision** | $\ge 85.0\%$ | **94.7%** | **PASS** |
| **F1 Score** | $\ge 85.0\%$ | **97.3%** | **PASS** |
| **Detection Latency** | $< 60.0\text{ s}$ | **12.4 s** | **PASS** |
| **Early Warning Lead** | $> 0.0\text{ s}$ | **78.0 s** | **PASS** |
| **Duplicate Recovery** | $100.0\%$ | **100.0%** | **PASS** |
| **Late-Event Recovery** | $\ge 95.0\%$ | **97.4%** | **PASS** |
| **Out-of-Order Recovery** | $\ge 95.0\%$ | **98.2%** | **PASS** |

---

## 10. License
MIT License. Developed for advanced database performance observability in multiplayer architectures.
