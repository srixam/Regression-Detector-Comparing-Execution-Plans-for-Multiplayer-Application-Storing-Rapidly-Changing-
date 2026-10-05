"""
QueryGuard Edge-Case Suite
Evaluates non-trivial edge cases:
1. Plan Telemetry Corruption (Malformed JSON / Truncated / Invalid Plan Trees)
2. Mid-Stream Schema Migration Rollback (Bimodal Window / Rolling Recovery)
3. Large Result Sets with Memory Sort Disk Spills (external merge sort)
"""

import sys
import os
import json
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from simulator.query_generator import QUERIES, KEY_TO_FINGERPRINT
from simulator.plan_generator import get_baseline_plan, extract_plan_metrics
from detector.plan_comparator import plan_comparator
from detector.scoring import scorer
from detector.evidence import evidence_engine
from detector.root_cause import root_cause_engine
from detector.thresholds import config
from backend.models.domain import Severity

class EdgeCaseEvaluator:
    def __init__(self):
        pass

    def run_plan_corruption_case(self) -> Dict[str, Any]:
        """
        Edge Case 1: Corrupted or Malformed Plan Source
        Tests that corrupted plans do not crash the system, and that scoring falls back
        gracefully to latency & catalog statistics with adjusted confidence.
        """
        baseline_plan = get_baseline_plan("get_active_player_session")
        corrupted_payloads = [
            "MALFORMED_PLAN_STRING",
            {"Status": "Database plan extraction timed out"},
            {"Plan": "NOT_A_DICTIONARY"},
            [],
            None
        ]

        results = []
        for payload in corrupted_payloads:
            # Plan comparator must safely handle without exception
            diff = plan_comparator.compare_plans(baseline_plan, payload)
            
            # Scorer evaluates with has_plan_source = False
            baseline = {"baseline_p95": 42.0}
            features = {
                "p95": 98.0, # 133% increase
                "has_plan_source": False,
                "has_release_source": True,
                "index_status": "active",
                "cardinality_error": 0.0,
                "workload_level": 1.0
            }
            score_res = scorer.compute_score(baseline, features, diff, persistence_count=2)
            results.append({
                "payload_type": type(payload).__name__,
                "diff_summary": diff["diff_summary"],
                "plan_changed": diff["plan_changed"],
                "severity": score_res["severity"].value,
                "confidence": score_res["confidence"],
                "active_weights": list(score_res["active_weights"].keys())
            })

        return {
            "edge_case": "plan_corruption",
            "passed": all(r["severity"] in ["WARNING", "HIGH", "CRITICAL"] and "plan" not in r["active_weights"] for r in results),
            "details": results
        }

    def run_migration_rollback_case(self) -> Dict[str, Any]:
        """
        Edge Case 2: Mid-Stream Migration Rollback (v2.3.1-rollback)
        Simulates an operational rollback during an active observation window.
        Bimodal latency distribution (50% regressed, 50% recovered) with rollback release correlation.
        """
        b_p95 = 42.0
        # Bimodal execution: half at 190ms (index dropped), half at 42ms (index restored)
        latencies = [190.0] * 30 + [42.0] * 30
        p95_val = sorted(latencies)[int(0.95 * len(latencies))]
        
        baseline = {"baseline_p95": b_p95}
        features = {
            "p50": 42.0,
            "p95": p95_val,
            "has_plan_source": True,
            "has_release_source": True,
            "index_status": "active", # restored by rollback
            "cardinality_error": 0.0,
            "workload_level": 1.0,
            "release_correlated": True
        }
        
        baseline_plan = get_baseline_plan("get_active_player_session")
        diff = plan_comparator.compare_plans(baseline_plan, baseline_plan)

        release_info = {
            "version": "v2.3.1-rollback",
            "is_correlated": True,
            "is_rollback": True,
            "schema_change": True,
            "formatted_delta": "3m 12s"
        }

        score_res = scorer.compute_score(baseline, features, diff, persistence_count=1)
        root_cause, rc_conf = root_cause_engine.determine_root_cause(
            features, diff, score_res, release_info
        )

        return {
            "edge_case": "migration_rollback",
            "passed": (score_res["severity"] in [Severity.WARNING, Severity.HIGH]) and ("v2.3.1-rollback" in root_cause or "release" in root_cause.lower()),
            "severity": score_res["severity"].value,
            "root_cause": root_cause,
            "bimodal_p95": p95_val,
            "confidence": score_res["confidence"]
        }

    def run_large_result_disk_spill_case(self) -> Dict[str, Any]:
        """
        Edge Case 3: Large Result Set with Disk Spill (external merge sort)
        Execution plan operator remains 'Sort' / 'Index Scan', but work_mem is exceeded,
        causing temp file disk spills and massive buffer read explosions.
        """
        baseline_plan = get_baseline_plan("region_leaderboard")
        
        # Real PostgreSQL plan representation with disk spill
        disk_spill_plan = {
            "Plan": {
                "Node Type": "Sort",
                "Startup Cost": 850.00,
                "Total Cost": 3400.00,
                "Plan Rows": 10000,
                "Actual Rows": 10000,
                "Actual Total Time": 145.2,
                "Sort Method": "external merge",
                "Sort Space Used": 5200,
                "Sort Space Type": "Disk",
                "Shared Hit Blocks": 120,
                "Shared Read Blocks": 2450,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "players",
                        "Index Name": "idx_players_region_skill",
                        "Startup Cost": 0.42,
                        "Total Cost": 1250.00,
                        "Plan Rows": 10000,
                        "Actual Rows": 10000,
                        "Shared Hit Blocks": 120,
                        "Shared Read Blocks": 1500
                    }
                ]
            }
        }

        diff = plan_comparator.compare_plans(baseline_plan, disk_spill_plan)
        
        baseline = {"baseline_p95": 110.0}
        features = {
            "p95": 380.0, # 245% increase due to disk IO
            "has_plan_source": True,
            "has_release_source": True,
            "index_status": "active",
            "cardinality_error": 0.0,
            "workload_level": 1.0,
            "release_correlated": False
        }

        score_res = scorer.compute_score(baseline, features, diff, persistence_count=2)

        return {
            "edge_case": "disk_spill",
            "passed": diff["is_significant_regression"] and score_res["severity"] in [Severity.HIGH, Severity.CRITICAL],
            "plan_penalty": diff["plan_score_penalty"],
            "is_significant": diff["is_significant_regression"],
            "severity": score_res["severity"].value,
            "read_blocks_diff": diff["read_blocks_diff"],
            "diff_summary": diff["diff_summary"]
        }

    def run_all(self) -> Dict[str, Any]:
        c1 = self.run_plan_corruption_case()
        c2 = self.run_migration_rollback_case()
        c3 = self.run_large_result_disk_spill_case()
        
        all_passed = c1["passed"] and c2["passed"] and c3["passed"]
        return {
            "all_edge_cases_passed": all_passed,
            "cases": {
                "plan_corruption": c1,
                "migration_rollback": c2,
                "disk_spill": c3
            }
        }

edge_cases = EdgeCaseEvaluator()

if __name__ == "__main__":
    res = edge_cases.run_all()
    print("=" * 70)
    print("QUERYGUARD EDGE-CASE EVALUATION RESULTS")
    print("=" * 70)
    print(f"1. Plan Corruption Handling : {'PASS' if res['cases']['plan_corruption']['passed'] else 'FAIL'}")
    print(f"2. Migration Rollback Window: {'PASS' if res['cases']['migration_rollback']['passed'] else 'FAIL'}")
    print(f"3. Disk Spill & Sort Buffer : {'PASS' if res['cases']['disk_spill']['passed'] else 'FAIL'}")
    print(f"Overall Status              : {'ALL EDGE CASES PASSED' if res['all_edge_cases_passed'] else 'FAILURES DETECTED'}")
    print("=" * 70)
