"""
Tests for PostgreSQL Execution Plan Comparator and Diff Generator
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.plan_generator import get_baseline_plan, get_regressed_plan, extract_plan_metrics, compute_plan_hash
from detector.plan_comparator import plan_comparator

def test_extract_plan_metrics_baseline():
    plan = get_baseline_plan("get_active_player_session")
    metrics = extract_plan_metrics(plan)

    assert metrics["node_type"] == "Index Scan"
    assert metrics["relation"] == "game_sessions"
    assert metrics["index_name"] == "idx_player_session"
    assert metrics["total_cost"] == 8.30
    assert metrics["actual_rows"] == 1
    assert metrics["shared_hit_blocks"] == 4
    assert metrics["shared_read_blocks"] == 0
    assert len(metrics["plan_hash"]) == 16

def test_plan_comparison_index_scan_to_seq_scan():
    b_plan = get_baseline_plan("get_active_player_session")
    c_plan = get_regressed_plan("get_active_player_session", scenario="index_removed")

    diff = plan_comparator.compare_plans(b_plan, c_plan)

    assert diff["plan_changed"] is True
    assert diff["is_significant_regression"] is True
    assert diff["plan_score_penalty"] >= 0.95
    assert "Index Scan -> Seq Scan" in diff["diff_summary"]
    assert diff["cost_change_pct"] > 1000.0  # Cost jumped from 8.3 to 485.0
    assert "PLAN REGRESSION: Index Scan -> Seq Scan" in diff["human_readable_diff"]
    assert "Shared read blocks increased by +45" in diff["human_readable_diff"]

def test_plan_comparison_unchanged_plan():
    b_plan = get_baseline_plan("region_leaderboard")
    c_plan = get_baseline_plan("region_leaderboard")

    diff = plan_comparator.compare_plans(b_plan, c_plan)

    assert diff["plan_changed"] is False
    assert diff["is_significant_regression"] is False
    assert diff["plan_score_penalty"] == 0.0
    assert diff["diff_summary"] == "Plan Unchanged"
    assert diff["cost_change_pct"] == 0.0
