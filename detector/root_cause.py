"""
Root Cause Classification Engine
Analyzes signal concordance across plans, catalog states, statistics, and workloads
to infer the most likely root-cause diagnosis.
"""

from typing import Dict, Any, Tuple
from backend.models.domain import RootCause, Severity

class RootCauseEngine:
    def __init__(self):
        pass

    def determine_root_cause(
        self,
        features: Dict[str, Any],
        plan_diff: Dict[str, Any],
        score_details: Dict[str, Any],
        release_details: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Infers the primary root cause and confidence rating.
        """
        severity = score_details.get("severity", Severity.NORMAL)
        if severity == Severity.NORMAL:
            return RootCause.NORMAL_VARIATION.value, 0.95

        index_status = features.get("index_status", "active")
        plan_changed = plan_diff.get("plan_changed", False)
        is_significant_plan = plan_diff.get("is_significant_regression", False)
        card_error = features.get("cardinality_error", 0.0)
        stats_age = features.get("stats_age_hours", 0.0)
        workload_lvl = features.get("workload_level", 1.0)
        has_plan = score_details.get("has_plan", True)
        
        rel_correlated = release_details.get("is_correlated", False) if release_details else False
        schema_change = release_details.get("schema_change", False) if release_details else False

        # 1. Missing / Invalid Index Root Cause
        # High confidence if index is reported missing/invalid, or plan changed from Index Scan -> Seq Scan
        if index_status in ["missing", "invalid"] or (is_significant_plan and "Seq Scan" in plan_diff.get("diff_summary", "")):
            if rel_correlated and schema_change:
                return "Missing index after schema deployment", 0.96
            if index_status == "invalid":
                return "Missing index or invalid index definition", 0.93
            return "Missing index or optimizer forced table scan", 0.92

        # 2. Stale Statistics / Cardinality Drift
        # Large estimation discrepancy without an explicit dropped index
        if card_error >= 5.0 or (card_error >= 2.0 and stats_age > 12.0):
            return "Stale optimizer statistics or altered data distribution", 0.88

        # 3. Workload Spike / Resource Contention
        # Execution plan remains identical, but latency increased under heavy load or concurrency
        if not plan_changed and (workload_lvl > 2.0 or features.get("p95", 0.0) >= 35.0):
            return "High query concurrency / buffer contention", 0.91

        # 4. Release Correlation without explicit plan regression
        if rel_correlated:
            ver = release_details.get("version", "recent")
            return f"Release-correlated regression following {ver}", 0.78

        # 5. Missing Telemetry Source Fallback
        if not has_plan:
            return "Latency regression detected (execution-plan telemetry unavailable)", 0.65

        # 6. General Performance Degradation
        return "Uncategorized execution latency regression", 0.70

root_cause_engine = RootCauseEngine()
