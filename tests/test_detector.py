"""
Tests for Regression Detector, Scoring, Severity, and Evidence Generation
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from detector.scoring import scorer
from detector.evidence import evidence_engine
from detector.root_cause import root_cause_engine
from detector.thresholds import config
from backend.models.domain import Severity

def test_scoring_weights_sum_to_100():
    total_weights = (
        config.weight_latency +
        config.weight_plan +
        config.weight_cardinality +
        config.weight_index +
        config.weight_release_workload
    )
    assert total_weights == pytest.approx(100.0)

def test_normal_latency_yields_normal_severity():
    baseline = {"baseline_p95": 25.0}
    features = {"p95": 26.0, "has_plan_source": True, "has_release_source": True}
    plan_diff = {"plan_changed": False, "plan_score_penalty": 0.0}

    result = scorer.compute_score(baseline, features, plan_diff)
    assert result["severity"] == Severity.NORMAL
    assert result["regression_score"] < 30.0

def test_critical_regression_with_plan_and_latency_spike():
    baseline = {"baseline_p95": 25.0}
    # 400% latency spike + plan regression penalty
    features = {"p95": 125.0, "has_plan_source": True, "has_release_source": True}
    plan_diff = {"plan_changed": True, "plan_score_penalty": 1.0, "is_significant_regression": True}

    result = scorer.compute_score(baseline, features, plan_diff)
    assert result["severity"] == Severity.CRITICAL
    assert result["regression_score"] >= 80.0

def test_cardinality_error_calculation():
    from pipeline.feature_builder import feature_builder
    # 45,000 actual vs 100 estimated
    err = feature_builder.compute_cardinality_error(estimated_rows=100.0, actual_rows=45000.0)
    assert err == pytest.approx(449.0)

def test_evidence_generation_is_factual_and_complete():
    baseline = {"baseline_p95": 42.0}
    features = {
        "p95": 191.0, "index_status": "missing", "index_name": "idx_player_session",
        "stats_age_hours": 19.0, "cardinality_error": 1.0, "workload_level": 1.0
    }
    plan_diff = {
        "plan_changed": True,
        "cost_change_pct": 5743.0,
        "baseline_metrics": {"node_type": "Index Scan"},
        "current_metrics": {"node_type": "Seq Scan"}
    }
    score_details = {"latency_change_pct": 354.8, "has_plan": True, "has_release": True}
    release_details = {
        "is_correlated": True, "version": "v2.3.1", "formatted_delta": "11m 24s", "schema_change": True
    }

    items = evidence_engine.generate_evidence("Get Active Player Session", baseline, features, plan_diff, score_details, release_details)
    assert any("Baseline p95 = 42.0 ms" in i for i in items)
    assert any("Current p95 = 191.0 ms" in i for i in items)
    assert any("Latency increased by +354.8%" in i for i in items)
    assert any("Index Scan → Seq Scan" in i for i in items)
    assert any("idx_player_session is unavailable" in i for i in items)
    assert any("Release v2.3.1" in i for i in items)

def test_root_cause_missing_index():
    features = {"index_status": "missing"}
    plan_diff = {"plan_changed": True, "is_significant_regression": True, "diff_summary": "Index Scan -> Seq Scan"}
    score_details = {"severity": Severity.CRITICAL, "has_plan": True}
    release_details = {"is_correlated": True, "schema_change": True, "version": "v2.3.1"}

    rc, conf = root_cause_engine.determine_root_cause(features, plan_diff, score_details, release_details)
    assert "Missing index" in rc
    assert conf >= 0.90
