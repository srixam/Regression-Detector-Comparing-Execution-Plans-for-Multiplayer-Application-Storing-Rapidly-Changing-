"""
FastAPI REST API Endpoints for QueryGuard
Exposes endpoints for metrics, query catalog, plans, regressions, releases, data quality, and simulations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.services.storage import storage_service
from backend.services.simulation_service import simulation_service
from detector.detector_state import detector_state
from simulator.query_generator import QUERIES, get_all_queries, FINGERPRINT_TO_KEY, KEY_TO_FINGERPRINT
from simulator.plan_generator import get_baseline_plan, get_regressed_plan, extract_plan_metrics
from detector.plan_comparator import plan_comparator
from simulator.release_generator import release_tracker
from pipeline.data_quality import data_quality_tracker
from experiments.evaluation import evaluation_engine
from backend.schemas.payloads import (
    OverviewMetrics, QuerySummary, PlanComparisonResponse,
    SimulationStartRequest, SimulationResponse, EvaluationMetricsResponse, EventBatchRequest
)

router = APIRouter()

@router.get("/health", tags=["Health"])
def get_health() -> Dict[str, Any]:
    from database.connection import db
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_backend": "PostgreSQL" if db.is_postgres() else "SQLite/Fallback",
        "service": "QueryGuard API",
        "version": "2.0.0"
    }

@router.get("/metrics/overview", response_model=OverviewMetrics, tags=["Metrics"])
def get_metrics_overview():
    return storage_service.get_overview_metrics()

@router.get("/queries", response_model=List[QuerySummary], tags=["Queries"])
def get_queries():
    return storage_service.get_all_query_summaries()

@router.get("/queries/{query_id}", tags=["Queries"])
def get_query_detail(query_id: str):
    detail = storage_service.get_query_detail(query_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    return detail

@router.get("/regressions", tags=["Regressions"])
def get_regressions():
    return detector_state.get_active_alerts()

@router.get("/regressions/{regression_id}", tags=["Regressions"])
def get_regression_detail(regression_id: str):
    for alert in detector_state.get_active_alerts():
        if alert.get("regression_id") == regression_id:
            return alert
    raise HTTPException(status_code=404, detail=f"Regression alert {regression_id} not found")

@router.get("/plans/{query_id}", tags=["Plans"])
def get_query_plan(query_id: str):
    q_key = FINGERPRINT_TO_KEY.get(query_id, query_id)
    if q_key not in QUERIES:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    fp = QUERIES[q_key]["fingerprint"]
    plan = detector_state.get_plan(fp) or get_baseline_plan(q_key)
    return {
        "query_fingerprint": fp,
        "query_key": q_key,
        "plan_json": plan,
        "metrics": extract_plan_metrics(plan)
    }

@router.get("/plans/{query_id}/compare", response_model=PlanComparisonResponse, tags=["Plans"])
def compare_query_plan(query_id: str):
    q_key = FINGERPRINT_TO_KEY.get(query_id, query_id)
    if q_key not in QUERIES:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")

    fp = QUERIES[q_key]["fingerprint"]
    b_plan = get_baseline_plan(q_key)
    c_plan = detector_state.get_plan(fp) or b_plan

    diff = plan_comparator.compare_plans(b_plan, c_plan)
    b_meta = diff.get("baseline_metrics", {})
    c_meta = diff.get("current_metrics", {})

    return {
        "query_fingerprint": fp,
        "baseline_plan_hash": b_meta.get("plan_hash"),
        "current_plan_hash": c_meta.get("plan_hash"),
        "plan_changed": diff.get("plan_changed", False),
        "structural_diff": diff.get("human_readable_diff", ""),
        "baseline_node_type": b_meta.get("node_type"),
        "current_node_type": c_meta.get("node_type"),
        "baseline_total_cost": b_meta.get("total_cost", 0.0),
        "current_total_cost": c_meta.get("total_cost", 0.0),
        "cost_change_pct": diff.get("cost_change_pct", 0.0),
        "baseline_plan_json": b_plan,
        "current_plan_json": c_plan
    }

@router.get("/releases", tags=["Releases"])
def get_releases():
    return release_tracker.get_all_releases()

@router.get("/indexes", tags=["Catalog"])
def get_indexes():
    # Returns active catalog indexes
    return [
        {"index_name": "idx_player_session", "table_name": "game_sessions", "columns": "player_id, status", "status": "active"},
        {"index_name": "idx_sessions_server_status", "table_name": "game_sessions", "columns": "server_id, status", "status": "active"},
        {"index_name": "idx_players_region_skill", "table_name": "players", "columns": "region, skill_rating DESC", "status": "active"},
        {"index_name": "idx_game_events_session_time", "table_name": "game_events", "columns": "session_id, event_time DESC", "status": "active"},
        {"index_name": "idx_query_exec_fp_time", "table_name": "query_executions", "columns": "query_fingerprint, event_time DESC", "status": "active"}
    ]

@router.get("/statistics", tags=["Catalog"])
def get_statistics():
    return [
        {"table_name": "players", "row_count": 10000, "dead_tuples": 12, "last_analyze": "1 hour ago", "estimated_rows": 10000, "actual_rows": 10000},
        {"table_name": "game_sessions", "row_count": 1500, "dead_tuples": 85, "last_analyze": "1 hour ago", "estimated_rows": 1500, "actual_rows": 1500},
        {"table_name": "game_events", "row_count": 100000, "dead_tuples": 450, "last_analyze": "1 hour ago", "estimated_rows": 100000, "actual_rows": 100000}
    ]

@router.get("/data-quality", tags=["Data Quality"])
def get_data_quality():
    return data_quality_tracker.get_quality_report()

@router.get("/evaluation", response_model=EvaluationMetricsResponse, tags=["Evaluation"])
def get_evaluation(scenarios: int = Query(default=30, ge=10, le=100)):
    return evaluation_engine.run_benchmark(num_scenarios=scenarios)

@router.post("/events", tags=["Pipeline"])
def ingest_events(batch: EventBatchRequest):
    from pipeline.normalizer import normalizer
    norm = normalizer.normalize_batch(batch.events)
    return {
        "status": "ingested",
        "received_count": len(batch.events),
        "normalized_count": len(norm),
        "duplicates_dropped": len(batch.events) - len(norm)
    }

@router.post("/simulation/start", response_model=SimulationResponse, tags=["Simulation"])
def start_simulation(req: SimulationStartRequest):
    return run_simulation_scenario(req.scenario_name)

@router.post("/simulation/scenario/{scenario_name}", response_model=SimulationResponse, tags=["Simulation"])
def run_simulation_scenario(scenario_name: str):
    name = scenario_name.lower().replace("-", "_")
    if name in ["baseline", "run_baseline"]:
        res = simulation_service.run_baseline()
    elif name in ["index_regression", "index_removed", "dropped_index"]:
        res = simulation_service.run_index_regression()
    elif name in ["statistics_regression", "stale_statistics"]:
        res = simulation_service.run_statistics_regression()
    elif name in ["workload_spike", "workload"]:
        res = simulation_service.run_workload_spike()
    elif name in ["early_warning", "early_warning_drift"]:
        res = simulation_service.run_early_warning_simulation()
    elif name in ["duplicate_events", "duplicates"]:
        res = simulation_service.run_fault_injection("duplicate_events")
    elif name in ["delayed_events", "delayed"]:
        res = simulation_service.run_fault_injection("delayed_events")
    elif name in ["out_of_order_events", "out_of_order"]:
        res = simulation_service.run_fault_injection("out_of_order_events")
    elif name in ["missing_plan_source", "missing_plan"]:
        res = simulation_service.run_fault_injection("missing_plan_source")
    elif name in ["missing_release_source", "missing_release"]:
        res = simulation_service.run_fault_injection("missing_release_source")
    elif name in ["recovery", "restore"]:
        res = simulation_service.run_recovery()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown simulation scenario: {scenario_name}")

    return {
        "scenario_name": scenario_name,
        "status": res.get("status", "completed"),
        "events_generated": res.get("events_generated", 100),
        "events_processed": res.get("events_processed", 100),
        "regressions_detected": res.get("regressions_detected", 0),
        "recovery_status": res.get("recovery_status", "N/A"),
        "details": res.get("details", res)
    }
