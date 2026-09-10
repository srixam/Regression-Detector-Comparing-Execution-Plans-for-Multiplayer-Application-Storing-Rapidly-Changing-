# QueryGuard Methodology: Baseline, Features, Thresholds, and Scoring

## 1. Baseline Methodology
QueryGuard rejects using simple arithmetic averages for latency because database tail latency exhibits heavy skew in multiplayer workloads.

For each query fingerprint $fp$, QueryGuard establishes a baseline vector $B_{fp}$ computed over clean historical observation windows:
$$B_{fp} = \{ p50, p95, p99, \sigma_{lat}, N, H_{plan}, T_{node}, E_{rows}, A_{rows}, I_{used}, \tau_{stats}, W_{level} \}$$

- **Percentiles**: $p50, p95, p99$ are calculated from sorted durations $D = [d_1, d_2, \dots, d_N]$.
- **Plan Hash** $H_{plan}$: Deterministic SHA-256 digest of canonical operator-relation-index path tokens.
- **Index State** $I_{used}$: Registered catalog index name.

---

## 2. Feature Extraction & Engineering

### 2.1 Latency Delta
Given baseline percentile $p95_{base}$ and current window percentile $p95_{curr}$:
$$\Delta p95 = \frac{p95_{curr} - p95_{base}}{p95_{base}} \times 100\%$$

### 2.2 Cardinality Estimation Error
Quantifies optimizer model drift due to stale catalog statistics:
$$\epsilon_{card} = \frac{|ActualRows - EstimatedRows|}{\max(EstimatedRows, 1)}$$
- If $\epsilon_{card} \ge 2.0$, statistics drift is flagged.
- If $\epsilon_{card} \ge 10.0$, catastrophic optimizer misestimation is identified.

### 2.3 Structural Plan Difference
- Traversal of baseline vs current JSON execution tree.
- Transitions penalized based on severity:
  - `Index Scan -> Seq Scan`: Penalty = $1.0$ (Catastrophic)
  - `Index Only Scan -> Index Scan`: Penalty = $0.4$ (Minor)
  - `Hash Join -> Nested Loop`: Penalty = $0.6$ (Severe for large tables)
  - Index Dropped / Missing: Penalty = $0.95$

---

## 3. Hybrid Explainable Scoring Formulation

QueryGuard calculates a holistic regression score $S \in [0, 100]$ using five explainable signal dimensions:

$$S = \sum_{i=1}^{5} w_i \cdot s_i \cdot \phi_{norm}$$

| Signal Component | Default Weight ($w_i$) | Input Source | Primary Indicator |
|---|---|---|---|
| **Latency Increase** | 35% | Telemetry Percentiles | $\Delta p95 \ge 20\%$ |
| **Plan Regression** | 30% | EXPLAIN JSON Tree | Operator / Cost shift |
| **Cardinality Error** | 15% | EXPLAIN Actual vs Est | Optimizer drift / skew |
| **Index Availability** | 10% | Catalog Metadata | Dropped / missing index |
| **Release & Workload** | 10% | Deploy Log & QPS | Release timing / QPM spike |

### 3.1 Severity Classifications
- **NORMAL** ($0 \le S < 30$): Within normal operating variance ($\Delta p95 < 20\%$).
- **WARNING** ($30 \le S < 60$): Moderate degradation ($\Delta p95 \ge 20\%$).
- **HIGH** ($60 \le S < 80$): Persistent degradation ($\Delta p95 \ge 50\%$ persisting for $\ge 3$ consecutive windows).
- **CRITICAL** ($80 \le S \le 100$): Severe regression ($\Delta p95 \ge 100\%$ combined with significant plan regression such as `Index Scan -> Seq Scan`).

---

## 4. Graceful Degradation & Dynamic Weight Re-normalization

When upstream data sources are unavailable or delayed, QueryGuard dynamically re-scales active weights:
$$\phi_{norm} = \frac{100.0}{\sum_{j \in Available} w_j}$$

Confidence $C$ is calibrated down proportionally:
$$C = \left( \frac{\sum_{j \in Available} w_j}{100.0} \right) \cdot C_{base} \cdot \prod \delta_{penalty}$$

If the execution plan source is offline, QueryGuard continues alerting on latency and cardinality, reporting:
> *"Latency regression detected. Execution-plan evidence unavailable."*
