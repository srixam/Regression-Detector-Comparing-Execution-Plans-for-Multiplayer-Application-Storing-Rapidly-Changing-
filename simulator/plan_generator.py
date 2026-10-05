"""
Query Plan Generator and PostgreSQL Plan Extractor
Supports real PostgreSQL EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) outputs and
high-fidelity synthetic plans representing healthy and regressed states.
"""

import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from simulator.query_generator import QUERIES, generate_query_fingerprint

def compute_plan_hash(plan_node: Any) -> str:
    """
    Computes a deterministic hash of the plan structure based on operator types,
    relation names, and index names (ignoring transient runtime timings).
    """
    if not isinstance(plan_node, dict):
        return "corrupted_hash"
    elements = []
    
    def walk(node: Any):
        if not isinstance(node, dict):
            return
        node_type = node.get("Node Type", "Unknown")
        rel = node.get("Relation Name", "")
        idx = node.get("Index Name", "")
        elements.append(f"{node_type}:{rel}:{idx}")
        for child in node.get("Plans", []):
            walk(child)
            
    walk(plan_node)
    canonical = "->".join(elements)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

def extract_plan_metrics(plan_json: Any) -> Dict[str, Any]:
    """
    Extracts core metrics from PostgreSQL EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) structure.
    Defensively handles malformed or corrupted plan payloads.
    """
    if not isinstance(plan_json, dict):
        return {
            "node_type": "Corrupted / Malformed",
            "relation": "",
            "index_name": "none",
            "startup_cost": 0.0,
            "total_cost": 0.0,
            "estimated_rows": 1.0,
            "actual_rows": 1.0,
            "actual_time_ms": 0.0,
            "shared_hit_blocks": 0,
            "shared_read_blocks": 0,
            "plan_hash": "corrupted_plan",
            "has_disk_spill": False,
            "is_corrupted": True
        }

    root = plan_json.get("Plan", plan_json)
    if not isinstance(root, dict):
        root = {}
    
    node_type = root.get("Node Type", "Unknown")
    relation = root.get("Relation Name", "")
    index_name = root.get("Index Name", "")
    startup_cost = float(root.get("Startup Cost", 0.0))
    total_cost = float(root.get("Total Cost", 0.0))
    plan_rows = float(root.get("Plan Rows", 1.0))
    actual_rows = float(root.get("Actual Rows", 1.0))
    actual_time = float(root.get("Actual Total Time", 0.0))
    hit_blocks = int(root.get("Shared Hit Blocks", 0))
    read_blocks = int(root.get("Shared Read Blocks", 0))
    
    # Check for memory sort disk spills (e.g. Sort Space Type: Disk or external merge)
    sort_space_type = root.get("Sort Space Type", "")
    sort_method = root.get("Sort Method", "")
    has_disk_spill = ("Disk" in sort_space_type) or ("external" in sort_method.lower())

    # If root doesn't have relation or index, look into its direct child
    if not relation and "Plans" in root and isinstance(root["Plans"], list) and len(root["Plans"]) > 0:
        child = root["Plans"][0]
        if isinstance(child, dict):
            if not relation:
                relation = child.get("Relation Name", "")
            if not index_name:
                index_name = child.get("Index Name", "")
            if hit_blocks == 0:
                hit_blocks = int(child.get("Shared Hit Blocks", 0))
            if read_blocks == 0:
                read_blocks = int(child.get("Shared Read Blocks", 0))
            if not has_disk_spill:
                has_disk_spill = ("Disk" in child.get("Sort Space Type", "")) or ("external" in child.get("Sort Method", "").lower())

    plan_hash = compute_plan_hash(root)
    
    return {
        "node_type": node_type,
        "relation": relation,
        "index_name": index_name or "none",
        "startup_cost": startup_cost,
        "total_cost": total_cost,
        "estimated_rows": plan_rows,
        "actual_rows": actual_rows,
        "actual_time_ms": actual_time,
        "shared_hit_blocks": hit_blocks,
        "shared_read_blocks": read_blocks,
        "plan_hash": plan_hash,
        "has_disk_spill": has_disk_spill,
        "is_corrupted": False
    }

def get_baseline_plan(query_key_or_fp: str) -> Dict[str, Any]:
    """Returns the healthy baseline execution plan JSON for a query."""
    plans = {
        "get_active_player_session": {
            "Plan": {
                "Node Type": "Index Scan",
                "Relation Name": "game_sessions",
                "Index Name": "idx_player_session",
                "Startup Cost": 0.28,
                "Total Cost": 8.30,
                "Plan Rows": 1,
                "Plan Width": 142,
                "Actual Startup Time": 0.021,
                "Actual Total Time": 0.042,
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Index Cond": "((player_id = $1) AND (status = 'active'::text))",
                "Shared Hit Blocks": 4,
                "Shared Read Blocks": 0
            },
            "Planning Time": 0.082,
            "Execution Time": 0.051
        },
        "update_session_state": {
            "Plan": {
                "Node Type": "Update",
                "Relation Name": "game_sessions",
                "Startup Cost": 0.28,
                "Total Cost": 8.30,
                "Plan Rows": 1,
                "Plan Width": 142,
                "Actual Startup Time": 0.035,
                "Actual Total Time": 0.078,
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "game_sessions",
                        "Index Name": "game_sessions_pkey",
                        "Startup Cost": 0.28,
                        "Total Cost": 8.30,
                        "Plan Rows": 1,
                        "Actual Total Time": 0.040,
                        "Actual Rows": 1,
                        "Shared Hit Blocks": 3,
                        "Shared Read Blocks": 0
                    }
                ]
            },
            "Planning Time": 0.095,
            "Execution Time": 0.092
        },
        "get_recent_game_events": {
            "Plan": {
                "Node Type": "Limit",
                "Startup Cost": 0.29,
                "Total Cost": 25.40,
                "Plan Rows": 50,
                "Plan Width": 180,
                "Actual Startup Time": 0.045,
                "Actual Total Time": 0.320,
                "Actual Rows": 50,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "game_events",
                        "Index Name": "idx_game_events_session_time",
                        "Startup Cost": 0.29,
                        "Total Cost": 25.40,
                        "Plan Rows": 50,
                        "Actual Total Time": 0.310,
                        "Actual Rows": 50,
                        "Shared Hit Blocks": 8,
                        "Shared Read Blocks": 0
                    }
                ]
            },
            "Planning Time": 0.110,
            "Execution Time": 0.345
        },
        "region_leaderboard": {
            "Plan": {
                "Node Type": "Limit",
                "Startup Cost": 0.29,
                "Total Cost": 45.20,
                "Plan Rows": 100,
                "Plan Width": 48,
                "Actual Startup Time": 0.052,
                "Actual Total Time": 0.510,
                "Actual Rows": 100,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "players",
                        "Index Name": "idx_players_region_skill",
                        "Startup Cost": 0.29,
                        "Total Cost": 45.20,
                        "Plan Rows": 100,
                        "Actual Total Time": 0.490,
                        "Actual Rows": 100,
                        "Shared Hit Blocks": 12,
                        "Shared Read Blocks": 0
                    }
                ]
            },
            "Planning Time": 0.125,
            "Execution Time": 0.540
        },
        "get_active_sessions_on_server": {
            "Plan": {
                "Node Type": "Bitmap Heap Scan",
                "Relation Name": "game_sessions",
                "Index Name": "idx_sessions_server_status",
                "Startup Cost": 4.35,
                "Total Cost": 32.10,
                "Plan Rows": 45,
                "Plan Width": 142,
                "Actual Startup Time": 0.060,
                "Actual Total Time": 0.440,
                "Actual Rows": 42,
                "Actual Loops": 1,
                "Shared Hit Blocks": 10,
                "Shared Read Blocks": 0
            },
            "Planning Time": 0.090,
            "Execution Time": 0.465
        },
        "get_player_profile": {
            "Plan": {
                "Node Type": "Index Scan",
                "Relation Name": "players",
                "Index Name": "players_pkey",
                "Startup Cost": 0.29,
                "Total Cost": 8.30,
                "Plan Rows": 1,
                "Plan Width": 64,
                "Actual Startup Time": 0.020,
                "Actual Total Time": 0.038,
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Shared Hit Blocks": 3,
                "Shared Read Blocks": 0
            },
            "Planning Time": 0.070,
            "Execution Time": 0.045
        },
        "get_active_players_by_region": {
            "Plan": {
                "Node Type": "HashAggregate",
                "Startup Cost": 35.50,
                "Total Cost": 68.50,
                "Plan Rows": 6,
                "Plan Width": 40,
                "Actual Startup Time": 0.420,
                "Actual Total Time": 0.850,
                "Actual Rows": 6,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Index Only Scan",
                        "Relation Name": "game_sessions",
                        "Index Name": "idx_player_session",
                        "Startup Cost": 0.28,
                        "Total Cost": 32.50,
                        "Plan Rows": 900,
                        "Actual Total Time": 0.650,
                        "Actual Rows": 890,
                        "Shared Hit Blocks": 22,
                        "Shared Read Blocks": 0
                    }
                ]
            },
            "Planning Time": 0.115,
            "Execution Time": 0.880
        }
    }
    
    # Map fingerprint or key
    from simulator.query_generator import FINGERPRINT_TO_KEY
    key = FINGERPRINT_TO_KEY.get(query_key_or_fp, query_key_or_fp)
    return plans.get(key, plans["get_active_player_session"])

def get_regressed_plan(query_key_or_fp: str, scenario: str = "index_removed") -> Dict[str, Any]:
    """Returns the regressed execution plan JSON for a query under a failure scenario."""
    from simulator.query_generator import FINGERPRINT_TO_KEY
    key = FINGERPRINT_TO_KEY.get(query_key_or_fp, query_key_or_fp)

    if scenario == "index_removed":
        # Catastrophic Index Scan -> Seq Scan
        return {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "game_sessions",
                "Index Name": "none",
                "Startup Cost": 0.00,
                "Total Cost": 485.00,
                "Plan Rows": 1,
                "Plan Width": 142,
                "Actual Startup Time": 12.450,
                "Actual Total Time": 191.400,
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Filter": "((player_id = $1) AND (status = 'active'::text))",
                "Rows Removed by Filter": 1499,
                "Shared Hit Blocks": 185,
                "Shared Read Blocks": 45
            },
            "Planning Time": 0.065,
            "Execution Time": 191.520
        }
    elif scenario == "stale_statistics":
        # Optimizer severely underestimates rows (Estimated: 100, Actual: 45000), causing poor plan
        return {
            "Plan": {
                "Node Type": "Nested Loop",
                "Startup Cost": 0.58,
                "Total Cost": 9820.00,
                "Plan Rows": 100,
                "Plan Width": 142,
                "Actual Startup Time": 5.200,
                "Actual Total Time": 240.500,
                "Actual Rows": 45000,
                "Actual Loops": 1,
                "Shared Hit Blocks": 4200,
                "Shared Read Blocks": 680,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "players",
                        "Startup Cost": 0.00,
                        "Total Cost": 250.00,
                        "Plan Rows": 100,
                        "Actual Rows": 45000
                    }
                ]
            },
            "Planning Time": 0.450,
            "Execution Time": 241.100
        }
    elif scenario == "early_warning_drift":
        # Intermediate phase: Cost is rising (58.00), estimated rows drifting, latency slightly up
        return {
            "Plan": {
                "Node Type": "Bitmap Heap Scan",
                "Relation Name": "game_sessions",
                "Index Name": "idx_player_session",
                "Startup Cost": 8.50,
                "Total Cost": 58.20,
                "Plan Rows": 12,
                "Plan Width": 142,
                "Actual Startup Time": 1.200,
                "Actual Total Time": 14.500,
                "Actual Rows": 250,
                "Actual Loops": 1,
                "Shared Hit Blocks": 38,
                "Shared Read Blocks": 8
            },
            "Planning Time": 0.150,
            "Execution Time": 14.700
        }
    else:
        # Default fallback to baseline plan
        return get_baseline_plan(key)
