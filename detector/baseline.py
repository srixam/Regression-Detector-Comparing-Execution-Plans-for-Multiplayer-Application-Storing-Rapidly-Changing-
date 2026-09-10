"""
Query Baseline Engine
Establishes healthy historical reference distributions for each query fingerprint,
capturing latency percentiles (p50, p95, p99), execution plan hashes, index usage, and catalog status.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import statistics
from database.connection import db
from simulator.query_generator import get_all_queries, KEY_TO_FINGERPRINT
from simulator.plan_generator import get_baseline_plan, extract_plan_metrics

class BaselineEngine:
    def __init__(self):
        self._in_memory_baselines: Dict[str, Dict[str, Any]] = {}

    def calculate_baseline_from_executions(
        self,
        query_fingerprint: str,
        executions: List[Dict[str, Any]],
        plan_meta: Optional[Dict[str, Any]] = None,
        index_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates baseline summary metrics from clean, healthy execution telemetry.
        """
        durations = [float(e.get("duration_ms", 0.0)) for e in executions]
        if not durations:
            # Fallback default healthy distribution
            durations = [25.0]

        sorted_d = sorted(durations)
        n = len(sorted_d)

        def get_pct(p: float) -> float:
            idx = int(round((p / 100.0) * (n - 1)))
            return sorted_d[max(0, min(n - 1, idx))]

        p50 = get_pct(50)
        p95 = get_pct(95)
        p99 = get_pct(99)
        std_val = statistics.stdev(sorted_d) if n > 1 else 0.0

        plan_hash = plan_meta.get("plan_hash") if plan_meta else "none"
        plan_type = plan_meta.get("node_type") if plan_meta else "Index Scan"
        est_rows = float(plan_meta.get("estimated_rows", 1.0)) if plan_meta else 1.0
        act_rows = float(plan_meta.get("actual_rows", 1.0)) if plan_meta else 1.0

        baseline = {
            "query_fingerprint": query_fingerprint,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "baseline_p50": round(p50, 2),
            "baseline_p95": round(p95, 2),
            "baseline_p99": round(p99, 2),
            "std_latency": round(std_val, 2),
            "execution_count": n,
            "baseline_plan_hash": plan_hash,
            "baseline_plan_type": plan_type,
            "estimated_rows": est_rows,
            "actual_rows": act_rows,
            "index_used": index_used or "idx_player_session",
            "statistics_age_hours": 0.5,
            "workload_level": 1.0
        }

        self._in_memory_baselines[query_fingerprint] = baseline
        self.persist_baseline(baseline)
        return baseline

    def persist_baseline(self, baseline: Dict[str, Any]) -> None:
        try:
            sql = """
            INSERT INTO query_baselines (
                query_fingerprint, calculated_at, baseline_p50, baseline_p95, baseline_p99,
                std_latency, execution_count, baseline_plan_hash, baseline_plan_type,
                estimated_rows, actual_rows, index_used, statistics_age_hours, workload_level
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (query_fingerprint) DO UPDATE SET
                calculated_at = EXCLUDED.calculated_at,
                baseline_p50 = EXCLUDED.baseline_p50,
                baseline_p95 = EXCLUDED.baseline_p95,
                baseline_p99 = EXCLUDED.baseline_p99,
                std_latency = EXCLUDED.std_latency,
                execution_count = EXCLUDED.execution_count,
                baseline_plan_hash = EXCLUDED.baseline_plan_hash,
                baseline_plan_type = EXCLUDED.baseline_plan_type,
                estimated_rows = EXCLUDED.estimated_rows,
                actual_rows = EXCLUDED.actual_rows,
                index_used = EXCLUDED.index_used,
                statistics_age_hours = EXCLUDED.statistics_age_hours,
                workload_level = EXCLUDED.workload_level;
            """
            params = (
                baseline["query_fingerprint"],
                baseline["calculated_at"],
                baseline["baseline_p50"],
                baseline["baseline_p95"],
                baseline["baseline_p99"],
                baseline["std_latency"],
                baseline["execution_count"],
                baseline["baseline_plan_hash"],
                baseline["baseline_plan_type"],
                baseline["estimated_rows"],
                baseline["actual_rows"],
                baseline["index_used"],
                baseline["statistics_age_hours"],
                baseline["workload_level"]
            )
            db.execute(sql, params)
        except Exception:
            # If SQLite or schema differs, in-memory cache is safe
            pass

    def get_baseline(self, query_fingerprint: str) -> Optional[Dict[str, Any]]:
        if query_fingerprint in self._in_memory_baselines:
            return self._in_memory_baselines[query_fingerprint]

        try:
            row = db.fetch_one("SELECT * FROM query_baselines WHERE query_fingerprint = %s", (query_fingerprint,))
            if row:
                self._in_memory_baselines[query_fingerprint] = row
                return row
        except Exception:
            pass

        return None

    def initialize_default_baselines(self) -> None:
        """Seeds standard baselines for all 7 multiplayer queries."""
        from simulator.workload_generator import workload_gen
        for q in get_all_queries():
            fp = q["fingerprint"]
            key = q["key"]
            execs = workload_gen.generate_executions(count=200, mode="normal", regressed_query_key=key)
            filtered = [e for e in execs if e["query_fingerprint"] == fp]
            plan = get_baseline_plan(key)
            plan_meta = extract_plan_metrics(plan)
            self.calculate_baseline_from_executions(fp, filtered, plan_meta, q["index"])

baseline_engine = BaselineEngine()
