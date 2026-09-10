"""
Feature Builder Engine
Aggregates sliding-window execution metrics, execution plan features,
cardinality estimation errors, index health, catalog stats, and release correlations.
"""

import math
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class FeatureBuilder:
    def __init__(self):
        pass

    def compute_percentiles(self, values: List[float]) -> Dict[str, float]:
        if not values:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "std": 0.0, "count": 0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        def get_p(pct: float) -> float:
            idx = int(round((pct / 100.0) * (n - 1)))
            return sorted_vals[max(0, min(n - 1, idx))]

        mean_val = sum(sorted_vals) / n
        std_val = statistics.stdev(sorted_vals) if n > 1 else 0.0

        return {
            "p50": round(get_p(50), 3),
            "p95": round(get_p(95), 3),
            "p99": round(get_p(99), 3),
            "mean": round(mean_val, 3),
            "std": round(std_val, 3),
            "count": n
        }

    def compute_cardinality_error(self, estimated_rows: float, actual_rows: float) -> float:
        """
        cardinality_error = abs(actual_rows - estimated_rows) / max(estimated_rows, 1)
        """
        return abs(actual_rows - estimated_rows) / max(estimated_rows, 1.0)

    def build_features(
        self,
        executions: List[Dict[str, Any]],
        plan_meta: Optional[Dict[str, Any]] = None,
        index_meta: Optional[Dict[str, Any]] = None,
        stats_meta: Optional[Dict[str, Any]] = None,
        release_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive feature vector for a query in an observation window.
        """
        latencies = [float(e.get("duration_ms", 0.0)) for e in executions]
        lat_stats = self.compute_percentiles(latencies)

        # Workload metrics
        workload_levels = [float(e.get("workload_level", 1.0)) for e in executions]
        avg_workload = (sum(workload_levels) / len(workload_levels)) if workload_levels else 1.0

        # Plan metrics
        node_type = plan_meta.get("node_type", "Unknown") if plan_meta else "Unavailable"
        plan_hash = plan_meta.get("plan_hash", "none") if plan_meta else "none"
        total_cost = float(plan_meta.get("total_cost", 0.0)) if plan_meta else 0.0
        startup_cost = float(plan_meta.get("startup_cost", 0.0)) if plan_meta else 0.0
        estimated_rows = float(plan_meta.get("estimated_rows", 1.0)) if plan_meta else 1.0
        actual_rows = float(plan_meta.get("actual_rows", 1.0)) if plan_meta else 1.0
        
        card_error = self.compute_cardinality_error(estimated_rows, actual_rows)

        # Index metrics
        index_status = index_meta.get("status", "active") if index_meta else "active"
        index_name = index_meta.get("index_name", "unknown") if index_meta else "unknown"

        # Statistics metrics
        stats_age_hours = 0.0
        dead_tuples = 0
        if stats_meta:
            dead_tuples = int(stats_meta.get("dead_tuples", 0))
            last_analyze = stats_meta.get("last_analyze")
            if last_analyze:
                try:
                    dt = datetime.fromisoformat(last_analyze)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    stats_age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
                except Exception:
                    stats_age_hours = 0.0

        # Release metrics
        release_id = release_meta.get("release_id") if release_meta else None
        release_correlated = release_meta.get("is_correlated", False) if release_meta else False

        return {
            "p50": lat_stats["p50"],
            "p95": lat_stats["p95"],
            "p99": lat_stats["p99"],
            "mean": lat_stats["mean"],
            "std": lat_stats["std"],
            "count": lat_stats["count"],
            "workload_level": round(avg_workload, 2),
            "plan_hash": plan_hash,
            "node_type": node_type,
            "total_cost": total_cost,
            "startup_cost": startup_cost,
            "estimated_rows": estimated_rows,
            "actual_rows": actual_rows,
            "cardinality_error": round(card_error, 2),
            "index_name": index_name,
            "index_status": index_status,
            "stats_age_hours": round(stats_age_hours, 2),
            "dead_tuples": dead_tuples,
            "release_id": release_id,
            "release_correlated": release_correlated,
            "has_plan_source": plan_meta is not None and plan_meta.get("source_status") != "unavailable",
            "has_release_source": release_meta is not None
        }

feature_builder = FeatureBuilder()
