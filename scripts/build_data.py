#!/usr/bin/env python3
"""
QueryGuard Data Build Pipeline
One-command script to populate data/raw/, data/processed/, and data/ground_truth/
with realistic telemetry events, execution plans, sliding window features, and labeled benchmarks.
"""

import os
import sys
import json
import random
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from simulator.query_generator import QUERIES, KEY_TO_FINGERPRINT
from simulator.workload_generator import workload_gen
from simulator.plan_generator import get_baseline_plan, get_regressed_plan, extract_plan_metrics
from simulator.fault_injector import fault_injector
from pipeline.normalizer import normalizer
from pipeline.deduplicator import deduplicator
from pipeline.ordering import order_manager
from pipeline.feature_builder import feature_builder
from detector.baseline import baseline_engine

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
GROUND_TRUTH_DIR = os.path.join(DATA_DIR, "ground_truth")

def ensure_directories():
    for d in [RAW_DIR, PROCESSED_DIR, GROUND_TRUTH_DIR]:
        os.makedirs(d, exist_ok=True)

def build_raw_data():
    print("[1/3] Generating Raw Datasets (data/raw/)...")
    
    # 1. Raw Query Executions (~1200 records across queries)
    raw_executions = []
    for mode in ["normal", "index_regression", "statistics_regression", "workload_spike"]:
        count = 350 if mode == "normal" else 200
        execs = workload_gen.generate_executions(count=count, mode=mode)
        raw_executions.extend(execs)
    
    raw_exec_file = os.path.join(RAW_DIR, "raw_executions.json")
    with open(raw_exec_file, "w") as f:
        json.dump(raw_executions, f, indent=2)
    print(f"  -> Generated {len(raw_executions)} executions -> {raw_exec_file} ({os.path.getsize(raw_exec_file):,} bytes)")

    # 2. Raw Game Telemetry Events (~600 player session events)
    game_events = []
    now = datetime.now(timezone.utc)
    event_types = ["session_connect", "player_action", "zone_transition", "item_pickup", "score_update", "session_disconnect"]
    for i in range(600):
        t_offset = random.randint(0, 3600)
        e_time = now - timedelta(seconds=t_offset)
        ing_delay = random.uniform(0.01, 1.2)
        game_events.append({
            "event_id": f"evt-{i+1:06d}",
            "player_id": random.randint(1001, 1999),
            "session_id": f"sess-{random.randint(500, 600)}",
            "server_id": f"srv-us-east-{random.randint(1, 4)}",
            "event_type": random.choice(event_types),
            "payload": {
                "coord_x": round(random.uniform(-500.0, 500.0), 2),
                "coord_y": round(random.uniform(-500.0, 500.0), 2),
                "health": random.randint(50, 100),
                "ping_ms": round(random.uniform(15.0, 85.0), 1)
            },
            "event_time": e_time.isoformat(),
            "ingestion_time": (e_time + timedelta(seconds=ing_delay)).isoformat()
        })
    
    raw_events_file = os.path.join(RAW_DIR, "raw_game_events.json")
    with open(raw_events_file, "w") as f:
        json.dump(game_events, f, indent=2)
    print(f"  -> Generated {len(game_events)} game events -> {raw_events_file} ({os.path.getsize(raw_events_file):,} bytes)")

    # 3. Raw Execution Plans (PostgreSQL EXPLAIN JSON trees)
    plans_catalog = {}
    for q_key, q_info in QUERIES.items():
        plans_catalog[q_key] = {
            "query_name": q_info["name"],
            "query_fingerprint": KEY_TO_FINGERPRINT[q_key],
            "baseline_plan": get_baseline_plan(q_key),
            "regressed_plans": {
                "index_removed": get_regressed_plan(q_key, "index_removed"),
                "stale_statistics": get_regressed_plan(q_key, "stale_statistics")
            }
        }
    
    raw_plans_file = os.path.join(RAW_DIR, "raw_plans.json")
    with open(raw_plans_file, "w") as f:
        json.dump(plans_catalog, f, indent=2)
    print(f"  -> Generated {len(plans_catalog)} query plan trees -> {raw_plans_file} ({os.path.getsize(raw_plans_file):,} bytes)")

    return raw_executions

def build_processed_data(raw_executions):
    print("[2/3] Processing Telemetry & Feature Vectors (data/processed/)...")
    
    # 1. Normalized and Deduplicated Telemetry
    normalized_records = normalizer.normalize_batch(raw_executions)
    
    processed_telemetry_file = os.path.join(PROCESSED_DIR, "normalized_telemetry.json")
    with open(processed_telemetry_file, "w") as f:
        json.dump(normalized_records, f, indent=2)
    print(f"  -> Normalized {len(normalized_records)} execution records -> {processed_telemetry_file} ({os.path.getsize(processed_telemetry_file):,} bytes)")

    # 2. Query Feature Matrix across queries
    feature_matrix = {}
    for q_key, q_info in QUERIES.items():
        q_fp = KEY_TO_FINGERPRINT[q_key]
        q_execs = [r["raw_payload"] for r in normalized_records if r["raw_payload"].get("query_fingerprint") == q_fp]
        
        plan = get_baseline_plan(q_key)
        plan_meta = extract_plan_metrics(plan)
        features = feature_builder.build_features(
            executions=q_execs,
            plan_meta=plan_meta,
            index_meta={"index_name": q_info["index"], "status": "active"}
        )
        feature_matrix[q_key] = {
            "query_name": q_info["name"],
            "query_fingerprint": q_fp,
            "feature_vector": features,
            "window_size": len(q_execs),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    feature_matrix_file = os.path.join(PROCESSED_DIR, "feature_matrix.json")
    with open(feature_matrix_file, "w") as f:
        json.dump(feature_matrix, f, indent=2)
    print(f"  -> Extracted {len(feature_matrix)} feature vectors -> {feature_matrix_file} ({os.path.getsize(feature_matrix_file):,} bytes)")

def build_ground_truth_data():
    print("[3/3] Generating Ground-Truth Benchmark Scenarios (data/ground_truth/)...")
    
    scenarios = []
    query_keys = list(QUERIES.keys())
    rng = random.Random(42)
    
    scenario_configs = [
        ("normal", False, "NORMAL", "Healthy workload execution within baseline boundaries"),
        ("index_removed", True, "CRITICAL", "Index dropped; query execution path transitioned from Index Scan to Seq Scan"),
        ("stale_statistics", True, "HIGH", "Severe cardinality estimation error (>2.0x) due to un-analyzed table mutations"),
        ("workload_spike", True, "WARNING", "Traffic surge without execution plan change"),
        ("minor_jitter", False, "NORMAL", "Transient latency fluctuation (+22%) suppressed by 2-window persistence check"),
        ("missing_plan", True, "WARNING", "Telemetry pipeline plan source unavailable; degraded fallback scoring active")
    ]

    for i in range(50):
        q_key = rng.choice(query_keys)
        scen_type, is_reg, exp_sev, desc = rng.choice(scenario_configs)
        
        scenarios.append({
            "scenario_id": f"gt-scen-{i+1:03d}",
            "scenario_type": scen_type,
            "query_key": q_key,
            "query_name": QUERIES[q_key]["name"],
            "query_fingerprint": KEY_TO_FINGERPRINT[q_key],
            "is_regression_ground_truth": is_reg,
            "expected_severity": exp_sev,
            "description": desc,
            "injected_fault": scen_type if scen_type != "normal" else "none",
            "eval_window_seconds": 60,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    gt_file = os.path.join(GROUND_TRUTH_DIR, "labeled_scenarios.json")
    with open(gt_file, "w") as f:
        json.dump(scenarios, f, indent=2)
    print(f"  -> Built {len(scenarios)} labeled ground truth scenarios -> {gt_file} ({os.path.getsize(gt_file):,} bytes)")

def main():
    print("=" * 70)
    print("QUERYGUARD ONE-COMMAND DATA BUILD PIPELINE")
    print(f"Target Directory: {DATA_DIR}")
    print("=" * 70)
    ensure_directories()
    raw_execs = build_raw_data()
    build_processed_data(raw_execs)
    build_ground_truth_data()
    print("=" * 70)
    print("DATA BUILD PIPELINE COMPLETED SUCCESSFULLY.")
    print("=" * 70)

if __name__ == "__main__":
    main()
