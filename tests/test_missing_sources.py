"""
Tests for Graceful Degradation under Missing or Delayed Telemetry Sources
Validates that QueryGuard remains operational when plans, releases, or index metadata are missing.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from detector.scoring import scorer
from detector.evidence import evidence_engine
from backend.models.domain import Severity

def test_missing_plan_source_graceful_degradation():
    baseline = {"baseline_p95": 25.0}
    # 250% latency increase, but plan source is unavailable
    features = {
        "p95": 87.5,
        "has_plan_source": False,
        "has_release_source": True,
        "cardinality_error": 0.0,
        "index_status": "active",
        "index_name": "idx_player_session",
        "stats_age_hours": 1.0,
        "workload_level": 1.0
    }
    plan_diff = {"plan_changed": False, "plan_score_penalty": 0.0}

    # Should dynamically re-weight available signals
    result = scorer.compute_score(baseline, features, plan_diff)
    assert result["severity"] in [Severity.HIGH, Severity.WARNING]
    # Confidence should be appropriately lower than full telemetry (0.96)
    assert result["confidence"] < 0.85
    assert result["confidence"] >= 0.50

    # Evidence items should state that plan is unavailable
    score_details = {"latency_change_pct": 250.0, "has_plan": False, "has_release": True}
    evidence = evidence_engine.generate_evidence("Get Active Player Session", baseline, features, plan_diff, score_details, None)
    assert any("Execution-plan evidence unavailable" in item for item in evidence)

def test_missing_release_source_graceful_degradation():
    baseline = {"baseline_p95": 25.0}
    features = {
        "p95": 80.0,
        "has_plan_source": True,
        "has_release_source": False,
        "index_status": "active",
        "index_name": "idx_player_session",
        "cardinality_error": 0.0,
        "stats_age_hours": 1.0,
        "workload_level": 1.0
    }
    plan_diff = {"plan_changed": False, "plan_score_penalty": 0.0}

    result = scorer.compute_score(baseline, features, plan_diff)
    assert result["confidence"] < 0.95

    score_details = {"latency_change_pct": 220.0, "has_plan": True, "has_release": False}
    evidence = evidence_engine.generate_evidence("Get Active Player Session", baseline, features, plan_diff, score_details, None)
    assert any("Release correlation unavailable" in item for item in evidence)

def test_delayed_index_metadata():
    baseline = {"baseline_p95": 25.0}
    features = {
        "p95": 90.0,
        "has_plan_source": True,
        "has_release_source": True,
        "index_status": "delayed",
        "index_name": "idx_player_session",
        "cardinality_error": 0.0,
        "stats_age_hours": 1.0,
        "workload_level": 1.0
    }
    plan_diff = {"plan_changed": False, "plan_score_penalty": 0.0}

    score_details = {"latency_change_pct": 260.0, "has_plan": True, "has_release": True}
    evidence = evidence_engine.generate_evidence("Get Active Player Session", baseline, features, plan_diff, score_details, None)
    assert any("Index metadata pending/delayed from catalog" in item for item in evidence)
