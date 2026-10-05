"""
Unit Tests for QueryGuard Edge Cases:
1. Plan Corruption & Malformed Payloads
2. Mid-Stream Schema Migration Rollback
3. Memory Sort Disk Spills & Buffer Explosions
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.plan_generator import extract_plan_metrics, get_baseline_plan
from detector.plan_comparator import plan_comparator
from detector.scoring import scorer
from detector.root_cause import root_cause_engine
from backend.models.domain import Severity

def test_plan_corruption_does_not_crash_extractor():
    # Corrupted string payload
    meta_str = extract_plan_metrics("TRUNCATED_JSON_STREAM")
    assert meta_str["is_corrupted"] is True
    assert meta_str["node_type"] == "Corrupted / Malformed"

    # Corrupted dict without Plan key
    meta_dict = extract_plan_metrics({"Query": "SELECT *", "Status": "TIMEOUT"})
    assert meta_dict["is_corrupted"] is False
    assert meta_dict["node_type"] == "Unknown"

    # Non-dictionary root
    meta_none = extract_plan_metrics(None)
    assert meta_none["is_corrupted"] is True

def test_plan_comparator_handles_corrupted_plans():
    baseline_plan = get_baseline_plan("get_active_player_session")
    corrupted_plan = "CORRUPTED_PLAN_PAYLOAD"

    diff = plan_comparator.compare_plans(baseline_plan, corrupted_plan)
    assert diff["plan_changed"] is False
    assert "Corrupted" in diff["diff_summary"]

    # Scorer gracefully degrades without 'plan' in active weights
    baseline = {"baseline_p95": 25.0}
    features = {
        "p95": 60.0,
        "has_plan_source": False,
        "has_release_source": True,
        "index_status": "active",
        "cardinality_error": 0.0,
        "workload_level": 1.0
    }
    score_res = scorer.compute_score(baseline, features, diff, persistence_count=2)
    assert "plan" not in score_res["active_weights"]
    assert score_res["severity"] in [Severity.WARNING, Severity.HIGH]

def test_migration_rollback_detection():
    baseline = {"baseline_p95": 42.0}
    features = {
        "p50": 42.0,
        "p95": 190.0, # Bimodal latency
        "has_plan_source": True,
        "has_release_source": True,
        "index_status": "active", # Restored after rollback
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
        "schema_change": True
    }

    score_res = scorer.compute_score(baseline, features, diff, persistence_count=1)
    rc, conf = root_cause_engine.determine_root_cause(features, diff, score_res, release_info)

    assert "v2.3.1-rollback" in rc
    assert score_res["severity"] == Severity.WARNING

def test_large_result_disk_spill_detection():
    baseline_plan = get_baseline_plan("region_leaderboard")
    disk_spill_plan = {
        "Plan": {
            "Node Type": "Sort",
            "Startup Cost": 850.00,
            "Total Cost": 3400.00,
            "Plan Rows": 10000,
            "Actual Rows": 10000,
            "Sort Method": "external merge",
            "Sort Space Used": 5200,
            "Sort Space Type": "Disk",
            "Shared Hit Blocks": 120,
            "Shared Read Blocks": 2450
        }
    }

    diff = plan_comparator.compare_plans(baseline_plan, disk_spill_plan)
    assert diff["is_significant_regression"] is True
    assert diff["plan_score_penalty"] >= 0.75
    assert diff["read_blocks_diff"] > 2000
    assert "DISK SPILL" in diff["human_readable_diff"]
