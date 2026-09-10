"""
PostgreSQL Execution Plan Comparator & Diff Engine
Detects structural plan regressions, operator replacements (e.g., Index Scan -> Seq Scan),
index dropped/missing, cost explosions, and buffer I/O shifts.
"""

from typing import Dict, Any, Optional, Tuple
from simulator.plan_generator import extract_plan_metrics

class PlanComparator:
    def __init__(self):
        # Severity weights for specific operator transitions
        self.transition_penalties = {
            ("Index Scan", "Seq Scan"): 1.0,
            ("Index Only Scan", "Seq Scan"): 1.0,
            ("Bitmap Index Scan", "Seq Scan"): 0.8,
            ("Index Only Scan", "Index Scan"): 0.4,
            ("Hash Join", "Nested Loop"): 0.6,
            ("Merge Join", "Nested Loop"): 0.5,
        }

    def compare_plans(self, baseline_plan: Dict[str, Any], current_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares baseline and current PostgreSQL execution plans.
        Returns detailed structural diff, metric deltas, and plan change flags.
        """
        if not baseline_plan or not current_plan:
            return {
                "plan_changed": False,
                "is_significant_regression": False,
                "plan_score_penalty": 0.0,
                "diff_summary": "Plan telemetry unavailable for comparison",
                "human_readable_diff": "N/A (Missing plan)",
                "baseline_metrics": {},
                "current_metrics": {}
            }

        b_meta = extract_plan_metrics(baseline_plan)
        c_meta = extract_plan_metrics(current_plan)

        plan_changed = (b_meta["plan_hash"] != c_meta["plan_hash"])
        b_node = b_meta["node_type"]
        c_node = c_meta["node_type"]
        b_idx = b_meta["index_name"]
        c_idx = c_meta["index_name"]

        # Cost change
        b_cost = max(b_meta["total_cost"], 0.01)
        c_cost = c_meta["total_cost"]
        cost_change_pct = ((c_cost - b_cost) / b_cost) * 100.0

        # Buffer read change
        read_blocks_diff = c_meta["shared_read_blocks"] - b_meta["shared_read_blocks"]

        # Determine structural transition penalty
        transition_key = (b_node, c_node)
        penalty = self.transition_penalties.get(transition_key, 0.0)

        # Index disappearance penalty
        if b_idx != "none" and c_idx == "none" and b_node != c_node:
            penalty = max(penalty, 0.95)

        # Cost explosion penalty even if node type matches
        if cost_change_pct > 200.0:
            penalty = max(penalty, 0.70)
        elif cost_change_pct > 50.0:
            penalty = max(penalty, 0.40)

        is_significant = (penalty >= 0.60) or (plan_changed and cost_change_pct >= 100.0)

        # Generate Human-Readable Diff
        diff_lines = [
            "BEFORE:",
            f"  Operator: {b_node}",
            f"  Relation: {b_meta['relation'] or 'N/A'}",
            f"  Index:    {b_idx}",
            f"  Cost:     {b_meta['startup_cost']:.2f} .. {b_meta['total_cost']:.2f}",
            f"  Rows:     {b_meta['actual_rows']} (est: {b_meta['estimated_rows']})",
            f"  Buffers:  {b_meta['shared_hit_blocks']} hit, {b_meta['shared_read_blocks']} read",
            "",
            "AFTER:",
            f"  Operator: {c_node}",
            f"  Relation: {c_meta['relation'] or 'N/A'}",
            f"  Index:    {c_idx}",
            f"  Cost:     {c_meta['startup_cost']:.2f} .. {c_meta['total_cost']:.2f}",
            f"  Rows:     {c_meta['actual_rows']} (est: {c_meta['estimated_rows']})",
            f"  Buffers:  {c_meta['shared_hit_blocks']} hit, {c_meta['shared_read_blocks']} read",
            "",
            "ANALYSIS:"
        ]

        if b_node != c_node:
            diff_lines.append(f"  PLAN REGRESSION: {b_node} -> {c_node}")
        elif plan_changed:
            diff_lines.append(f"  OPERATOR CHANGE: Subtree modified (Hash {b_meta['plan_hash'][:8]} -> {c_meta['plan_hash'][:8]})")
        else:
            diff_lines.append("  PLAN UNCHANGED: Structure matches healthy baseline")

        if cost_change_pct != 0.0:
            diff_lines.append(f"  Cost Delta: {cost_change_pct:+.1f}%")
        if read_blocks_diff > 0:
            diff_lines.append(f"  I/O Degradation: Shared read blocks increased by +{read_blocks_diff}")

        summary = f"{b_node} -> {c_node}" if b_node != c_node else ("Subtree Changed" if plan_changed else "Plan Unchanged")

        return {
            "plan_changed": plan_changed,
            "is_significant_regression": is_significant,
            "plan_score_penalty": round(penalty, 2),
            "diff_summary": summary,
            "human_readable_diff": "\n".join(diff_lines),
            "cost_change_pct": round(cost_change_pct, 1),
            "read_blocks_diff": read_blocks_diff,
            "baseline_metrics": b_meta,
            "current_metrics": c_meta
        }

plan_comparator = PlanComparator()
