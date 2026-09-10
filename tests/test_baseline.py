"""
Tests for Query Baseline Engine
Validates percentile calculations (p50, p95, p99), persistence, and metadata extraction.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from detector.baseline import baseline_engine
from simulator.query_generator import QUERIES, KEY_TO_FINGERPRINT
from simulator.plan_generator import get_baseline_plan, extract_plan_metrics

def test_baseline_calculation_and_percentiles():
    # Synthetic durations
    executions = [{"duration_ms": val} for val in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]]
    q_key = "get_active_player_session"
    fp = KEY_TO_FINGERPRINT[q_key]
    plan = get_baseline_plan(q_key)
    plan_meta = extract_plan_metrics(plan)

    baseline = baseline_engine.calculate_baseline_from_executions(
        query_fingerprint=fp,
        executions=executions,
        plan_meta=plan_meta,
        index_used="idx_player_session"
    )

    assert baseline["query_fingerprint"] == fp
    assert baseline["baseline_p50"] == pytest.approx(50.0, abs=5.0)
    assert baseline["baseline_p95"] >= 90.0
    assert baseline["baseline_p99"] >= 95.0
    assert baseline["baseline_plan_type"] == "Index Scan"
    assert baseline["index_used"] == "idx_player_session"
    assert baseline["execution_count"] == 10

def test_baseline_persistence_and_retrieval():
    fp = "fp_test_mock_123"
    executions = [{"duration_ms": 25.0} for _ in range(5)]
    baseline = baseline_engine.calculate_baseline_from_executions(fp, executions)

    retrieved = baseline_engine.get_baseline(fp)
    assert retrieved is not None
    assert retrieved["query_fingerprint"] == fp
    assert retrieved["baseline_p50"] == 25.0
