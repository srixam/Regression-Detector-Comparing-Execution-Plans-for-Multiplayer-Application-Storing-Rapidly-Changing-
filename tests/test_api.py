"""
Tests for FastAPI Endpoints using TestClient
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "database_backend" in data

def test_metrics_overview_endpoint():
    resp = client.get("/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_queries_monitored" in data
    assert "avg_p95_latency_ms" in data
    assert "data_source_health" in data

def test_queries_endpoint():
    resp = client.get("/queries")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 7
    assert any(q["query_name"] == "Get Active Player Session" for q in data)

def test_plan_comparison_endpoint():
    resp = client.get("/plans/get_active_player_session/compare")
    assert resp.status_code == 200
    data = resp.json()
    assert "structural_diff" in data
    assert "baseline_total_cost" in data

def test_data_quality_endpoint():
    resp = client.get("/data-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_health_score" in data
    assert "duplicates_removed" in data

def test_simulation_scenario_index_regression():
    resp = client.post("/simulation/scenario/index_regression")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "regression_detected"
    assert data["regressions_detected"] >= 1

def test_evaluation_endpoint():
    resp = client.get("/evaluation?scenarios=15")
    assert resp.status_code == 200
    data = resp.json()
    assert "precision" in data
    assert "recall" in data
    assert "f1_score" in data
    assert "target_vs_measured" in data
