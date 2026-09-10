"""
Hybrid Explainable Regression Scoring Engine
Computes multidimensional regression scores (0 to 100) combining:
- Latency deltas (35%)
- Execution plan regressions (30%)
- Cardinality estimation errors (15%)
- Index availability (10%)
- Release & Workload correlations (10%)
Dynamically re-weights signals when sources are missing or delayed, scaling confidence appropriately.
"""

from typing import Dict, Any, Tuple
from detector.thresholds import config
from backend.models.domain import Severity

class RegressionScorer:
    def __init__(self):
        pass

    def compute_score(
        self,
        baseline: Dict[str, Any],
        features: Dict[str, Any],
        plan_diff: Dict[str, Any],
        persistence_count: int = 1
    ) -> Dict[str, Any]:
        """
        Calculates hybrid regression score, severity, subscores, and detector confidence.
        """
        b_p95 = max(float(baseline.get("baseline_p95", 25.0)), 0.1)
        c_p95 = float(features.get("p95", 25.0))
        latency_change_pct = ((c_p95 - b_p95) / b_p95) * 100.0

        # 1. Latency Subscore (0.0 to 1.0)
        if latency_change_pct <= 0.0:
            lat_sub = 0.0
        elif latency_change_pct >= config.latency_critical_pct:
            lat_sub = 1.0
        elif latency_change_pct >= config.latency_high_pct:
            # Scaled 0.6 to 1.0
            fraction = (latency_change_pct - config.latency_high_pct) / (config.latency_critical_pct - config.latency_high_pct)
            lat_sub = 0.6 + (0.4 * fraction)
        elif latency_change_pct >= config.latency_warning_pct:
            # Scaled 0.3 to 0.6
            fraction = (latency_change_pct - config.latency_warning_pct) / (config.latency_high_pct - config.latency_warning_pct)
            lat_sub = 0.3 + (0.3 * fraction)
        else:
            lat_sub = max(0.0, (latency_change_pct / config.latency_warning_pct) * 0.25)

        # 2. Plan Subscore (0.0 to 1.0)
        has_plan = features.get("has_plan_source", True)
        if has_plan:
            plan_sub = float(plan_diff.get("plan_score_penalty", 0.0))
            if plan_diff.get("plan_changed", False) and plan_sub == 0.0:
                plan_sub = 0.25
        else:
            plan_sub = 0.0

        # 3. Cardinality Subscore (0.0 to 1.0)
        card_error = float(features.get("cardinality_error", 0.0))
        if card_error >= 10.0:
            card_sub = 1.0
        elif card_error >= config.cardinality_error_threshold:
            card_sub = 0.4 + min(0.6, (card_error - config.cardinality_error_threshold) * 0.1)
        else:
            card_sub = 0.0

        # 4. Index Subscore (0.0 to 1.0)
        index_status = features.get("index_status", "active")
        if index_status == "missing":
            idx_sub = 1.0
        elif index_status == "delayed":
            idx_sub = 0.4
        elif index_status == "invalid":
            idx_sub = 0.8
        else:
            idx_sub = 0.0

        # 5. Release & Workload Subscore (0.0 to 1.0)
        has_release = features.get("has_release_source", True)
        rel_corr = features.get("release_correlated", False) if has_release else False
        workload_lvl = float(features.get("workload_level", 1.0))
        
        rel_workload_sub = 0.0
        if rel_corr:
            rel_workload_sub += 0.6
        if workload_lvl > 3.0:
            rel_workload_sub += 0.4
        rel_workload_sub = min(1.0, rel_workload_sub)

        # Dynamic re-normalization if data sources are missing
        active_weights = {}
        active_weights["latency"] = config.weight_latency
        if has_plan:
            active_weights["plan"] = config.weight_plan
        active_weights["cardinality"] = config.weight_cardinality
        active_weights["index"] = config.weight_index
        if has_release:
            active_weights["release_workload"] = config.weight_release_workload

        total_active_weight = sum(active_weights.values())
        norm_factor = 100.0 / total_active_weight if total_active_weight > 0 else 1.0

        # Compute weighted sum
        weighted_score = 0.0
        weighted_score += lat_sub * active_weights["latency"] * norm_factor
        if has_plan:
            weighted_score += plan_sub * active_weights["plan"] * norm_factor
        weighted_score += card_sub * active_weights["cardinality"] * norm_factor
        weighted_score += idx_sub * active_weights["index"] * norm_factor
        if has_release:
            weighted_score += rel_workload_sub * active_weights["release_workload"] * norm_factor

        final_score = max(0.0, min(100.0, round(weighted_score, 1)))

        # Confidence calculation
        # Normalized by active source weight with slight adjustments for metadata delays
        base_confidence = (total_active_weight / 100.0) * 0.96
        if index_status == "delayed":
            base_confidence *= 0.90
        confidence = round(max(0.40, min(0.98, base_confidence)), 2)

        # Severity classification
        # Default thresholds:
        # NORMAL: p95 increase < 20%
        # WARNING: p95 increase >= 20%
        # HIGH: p95 increase >= 50% and persists for at least 3 windows
        # CRITICAL: p95 increase >= 100% AND significant plan regression
        is_critical_rule = (latency_change_pct >= config.latency_critical_pct and plan_diff.get("is_significant_regression", False))
        
        if is_critical_rule or final_score >= config.score_critical_cutoff:
            severity = Severity.CRITICAL
            final_score = max(final_score, 82.0)
        elif (latency_change_pct >= config.latency_high_pct and persistence_count >= config.persistence_windows) or final_score >= config.score_high_cutoff:
            severity = Severity.HIGH
            final_score = max(final_score, 62.0)
        elif latency_change_pct >= config.latency_warning_pct or final_score >= config.score_warning_cutoff:
            severity = Severity.WARNING
        else:
            severity = Severity.NORMAL

        return {
            "regression_score": final_score,
            "severity": severity,
            "confidence": confidence,
            "latency_change_pct": round(latency_change_pct, 1),
            "subscores": {
                "latency": round(lat_sub, 2),
                "plan": round(plan_sub, 2),
                "cardinality": round(card_sub, 2),
                "index": round(idx_sub, 2),
                "release_workload": round(rel_workload_sub, 2)
            },
            "active_weights": active_weights,
            "has_plan": has_plan,
            "has_release": has_release
        }

scorer = RegressionScorer()
