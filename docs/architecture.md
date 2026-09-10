# QueryGuard Architecture Specification

QueryGuard is a specialized query-regression detection and root-cause observability platform engineered for multiplayer games and session-state systems storing rapidly changing player state in relational databases.

## 1. High-Level System Architecture

```
+-------------------------------------------------------------+
|                MULTIPLAYER WORKLOAD SIMULATOR               |
|  - 10,000+ Players (Pareto/Gaussian ratings)                |
|  - 1,500+ Game Sessions (Active, Completed, Abandoned)      |
|  - 100,000+ Game Events (Tick syncs, inputs, abilities)     |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                      EVENT GENERATOR                        |
|  - Query Execution Telemetry                                |
|  - Real PostgreSQL Execution Plans (EXPLAIN ANALYZE JSON)   |
|  - Index Metadata Tracking                                  |
|  - Table Statistics & Tuple Bloat Snapshots                 |
|  - Release Deployment History & Migration Flags             |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|              EVENT RELIABILITY & NORMALIZATION              |
|  - Deduplication Engine (LRU hash set, 100% idempotency)     |
|  - Chronological Timeline Reordering (by event_time)        |
|  - Watermarking & Lateness Detection                        |
|  - Data Quality Health Scorer (0-100%)                      |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                       FEATURE ENGINE                        |
|  - Latency Percentiles (p50, p95, p99, std, rolling window) |
|  - Plan Structural Features (hash, root operator, costs)    |
|  - Cardinality Error Ratio |Actual - Estimated| / Est       |
|  - Index Availability (active, missing, delayed)            |
|  - Workload Concurrency Multiplier (QPM)                    |
|  - Release Proximity Delta (seconds elapsed)                |
+-------------------------------------------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+             +-----------------------+
|    BASELINE ENGINE    |             |  REGRESSION DETECTOR  |
| - Clean reference     |             | - Hybrid Scoring      |
|   profile per query   |             | - Dynamic Weights     |
| - Stored in catalog   |             | - Severity (0-100)    |
+-----------------------+             +-----------------------+
            \                                     /
             +-----------------+-----------------+
                               |
                               v
+-------------------------------------------------------------+
|              EVIDENCE & ROOT CAUSE ENGINE                   |
|  - Un-fabricated factual evidence item generation           |
|  - Signal concordance hypothesis (Missing Index, Drift, etc)|
|  - Confidence calibration (0.0 to 1.0)                      |
|  - Graceful degradation notes when sources unavailable       |
+-------------------------------------------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+             +-----------------------+
|     FASTAPI REST      |             |     STREAMLIT UI      |
| - OpenAPI Docs        |             | - 8 SRE Dashboards    |
| - Telemetry Ingestion |             | - Plan Tree Visualizer|
| - Scenario Triggers   |             | - Control Room        |
+-----------------------+             +-----------------------+
```

---

## 2. Core Components

### 2.1 Database & Persistence
- **PostgreSQL 16**: Primary relational storage holding game state (`players`, `game_sessions`, `game_events`), query logs (`query_executions`, `query_plans`), and alerts (`regression_alerts`).
- **psycopg**: High-performance Python PostgreSQL driver executing real `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`.
- **Local SQLite Engine**: Built-in fallback allowing developers to run QueryGuard in VS Code without needing an active PostgreSQL daemon.

### 2.2 Pipeline & Reliability Layer
- **EventDeduplicator**: Maintains an LRU hash table of observed `event_id` and `payload_hash` keys. Duplicates are immediately discarded from analytics, ensuring state is never corrupted.
- **EventOrderManager**: Buffers and re-orders telemetry by `event_time`, ensuring chronological consistency even under severe network jitter or out-of-order delivery.
- **DataQualityTracker**: Measures missing upstream sources, calculating an overall data quality score.

### 2.3 Detector & Plan Comparator
- **PlanComparator**: Performs recursive traversal of PostgreSQL JSON operator trees, identifying structural changes (such as `Index Scan -> Seq Scan`), cost explosions, and disk buffer reads (`shared_read_blocks`).
- **Hybrid Scorer**: Merges latency deltas, plan regressions, estimation errors, index status, and release timing. Dynamically re-normalizes weights when sources are missing.
- **Evidence & Root Cause Engine**: Translates raw database measurements into structured human-readable explanations backed by verifiable facts.
