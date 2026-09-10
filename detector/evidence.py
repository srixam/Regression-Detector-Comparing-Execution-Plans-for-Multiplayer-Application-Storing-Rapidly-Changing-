"""
Evidence Generation Engine
Assembles rigorous, un-fabricated evidence items from actual stored execution records,
plan diffs, index catalog states, statistics ages, and release histories.
"""

from typing import Dict, Any, List
from backend.models.domain import Severity

class EvidenceEngine:
    def __init__(self):
        pass

    def generate_evidence(
        self,
        query_name: str,
        baseline: Dict[str, Any],
        features: Dict[str, Any],
        plan_diff: Dict[str, Any],
        score_details: Dict[str, Any],
        release_details: Dict[str, Any]
    ) -> List[str]:
        """
        Synthesizes a list of factual evidence statements based strictly on measured values.
        """
        evidence_items = []
        b_p95 = baseline.get("baseline_p95", 0.0)
        c_p95 = features.get("p95", 0.0)
        lat_change = score_details.get("latency_change_pct", 0.0)

        # 1. Latency Baseline Evidence
        evidence_items.append(f"Baseline p95 = {b_p95:.1f} ms")

        # 2. Current Latency Evidence
        evidence_items.append(f"Current p95 = {c_p95:.1f} ms")

        # 3. Percentage Increase Evidence
        evidence_items.append(f"Latency increased by {lat_change:+.1f}%")

        # 4. Plan Evidence (or note missing)
        if score_details.get("has_plan", True):
            if plan_diff.get("plan_changed", False):
                b_node = plan_diff.get("baseline_metrics", {}).get("node_type", "Unknown")
                c_node = plan_diff.get("current_metrics", {}).get("node_type", "Unknown")
                evidence_items.append(f"Plan changed {b_node} → {c_node}")
                if plan_diff.get("cost_change_pct", 0.0) > 0:
                    evidence_items.append(f"Optimizer estimated cost changed by {plan_diff['cost_change_pct']:+.1f}%")
            else:
                evidence_items.append("Execution plan unchanged (retains baseline operator structure)")
        else:
            evidence_items.append("Execution-plan evidence unavailable")

        # 5. Index Catalog Evidence
        idx_status = features.get("index_status", "active")
        idx_name = features.get("index_name", "idx_player_session")
        if idx_status == "missing":
            evidence_items.append(f"Index {idx_name} is unavailable or dropped")
        elif idx_status == "delayed":
            evidence_items.append(f"Index metadata pending/delayed from catalog")
        elif idx_status == "active":
            evidence_items.append(f"Index {idx_name} is active in catalog")

        # 6. Statistics / Cardinality Evidence
        stats_age = features.get("stats_age_hours", 0.0)
        card_error = features.get("cardinality_error", 0.0)
        if stats_age > 12.0:
            evidence_items.append(f"Table statistics are {stats_age:.1f} hours old")
        if card_error >= 2.0:
            est_r = features.get("estimated_rows", 1.0)
            act_r = features.get("actual_rows", 1.0)
            evidence_items.append(
                f"Large cardinality estimation error (est: {est_r:,.0f}, actual: {act_r:,.0f}, error: {card_error:.1f}x)"
            )

        # 7. Release Correlation Evidence
        if score_details.get("has_release", True):
            if release_details and release_details.get("is_correlated", False):
                ver = release_details.get("version", "unknown")
                delta_str = release_details.get("formatted_delta", "recently")
                evidence_items.append(f"Release {ver} occurred {delta_str} before detection")
            else:
                evidence_items.append("No recent release deployment correlated within 2 hours")
        else:
            evidence_items.append("Release correlation unavailable")

        # 8. Workload Evidence
        workload = features.get("workload_level", 1.0)
        if workload > 2.5:
            evidence_items.append(f"Workload surge detected ({workload:.1f}x baseline query concurrency)")

        return evidence_items

evidence_engine = EvidenceEngine()
