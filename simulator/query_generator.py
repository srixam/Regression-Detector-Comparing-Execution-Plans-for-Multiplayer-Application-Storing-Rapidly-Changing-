"""
Representative Multiplayer Queries & Query Fingerprint Generator
Generates and normalizes SQL queries for multiplayer game session state.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple
import random

# The 7 Representative Multiplayer Queries
QUERIES = {
    "get_active_player_session": {
        "name": "Get Active Player Session",
        "sql": "SELECT * FROM game_sessions WHERE player_id = %s AND status = 'active'",
        "table": "game_sessions",
        "index": "idx_player_session",
        "category": "critical_path_read",
        "sample_params": lambda: (f"ply-{random.randint(1, 10000):06d}",)
    },
    "update_session_state": {
        "name": "Update Session State",
        "sql": "UPDATE game_sessions SET updated_at = NOW(), status = %s WHERE session_id = %s",
        "table": "game_sessions",
        "index": "PRIMARY",
        "category": "high_frequency_write",
        "sample_params": lambda: ("active", f"ses-{random.randint(1, 1500):06d}")
    },
    "get_recent_game_events": {
        "name": "Get Recent Game Events",
        "sql": "SELECT * FROM game_events WHERE session_id = %s ORDER BY event_time DESC LIMIT 50",
        "table": "game_events",
        "index": "idx_game_events_session_time",
        "category": "event_log_read",
        "sample_params": lambda: (f"ses-{random.randint(1, 1500):06d}",)
    },
    "region_leaderboard": {
        "name": "Region Leaderboard",
        "sql": "SELECT player_id, skill_rating FROM players WHERE region = %s ORDER BY skill_rating DESC LIMIT 100",
        "table": "players",
        "index": "idx_players_region_skill",
        "category": "analytics_read",
        "sample_params": lambda: (random.choice(["us-east", "us-west", "eu-central", "eu-west", "ap-southeast", "ap-northeast"]),)
    },
    "get_active_sessions_on_server": {
        "name": "Get Active Sessions On Server",
        "sql": "SELECT * FROM game_sessions WHERE server_id = %s AND status = 'active'",
        "table": "game_sessions",
        "index": "idx_sessions_server_status",
        "category": "server_monitoring_read",
        "sample_params": lambda: (random.choice(["srv-na-01", "srv-na-02", "srv-eu-01", "srv-eu-02", "srv-ap-01", "srv-ap-02"]),)
    },
    "get_player_profile": {
        "name": "Get Player Profile",
        "sql": "SELECT * FROM players WHERE player_id = %s",
        "table": "players",
        "index": "PRIMARY",
        "category": "profile_read",
        "sample_params": lambda: (f"ply-{random.randint(1, 10000):06d}",)
    },
    "get_active_players_by_region": {
        "name": "Get Active Players by Region",
        "sql": "SELECT region, COUNT(*) as active_count FROM game_sessions WHERE status = 'active' GROUP BY region",
        "table": "game_sessions",
        "index": "idx_player_session",
        "category": "aggregate_read",
        "sample_params": lambda: ()
    }
}

def generate_query_fingerprint(sql: str) -> str:
    """
    Normalizes SQL by stripping comments, literal values, quoted strings, numbers,
    collapsing whitespace, and returning a stable SHA-256 fingerprint prefix.
    """
    normalized = sql.strip().upper()
    # Strip string literals
    normalized = re.sub(r"'[^']*'", "?", normalized)
    # Strip numeric literals
    normalized = re.sub(r"\b\d+\b", "?", normalized)
    # Strip parameter placeholders
    normalized = re.sub(r"%\w+", "?", normalized)
    normalized = re.sub(r"\$\d+", "?", normalized)
    # Collapse multiple whitespaces
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    # Generate 16-character hex hash
    fp_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"fp_{fp_hash}"

# Precompute query fingerprints
FINGERPRINT_TO_KEY = {}
KEY_TO_FINGERPRINT = {}

for key, meta in QUERIES.items():
    fp = generate_query_fingerprint(meta["sql"])
    meta["fingerprint"] = fp
    FINGERPRINT_TO_KEY[fp] = key
    KEY_TO_FINGERPRINT[key] = fp

def get_query_meta(key_or_fp: str) -> Dict[str, Any]:
    if key_or_fp in QUERIES:
        return QUERIES[key_or_fp]
    elif key_or_fp in FINGERPRINT_TO_KEY:
        return QUERIES[FINGERPRINT_TO_KEY[key_or_fp]]
    raise KeyError(f"Unknown query key or fingerprint: {key_or_fp}")

def get_all_queries() -> List[Dict[str, Any]]:
    return [
        {
            "key": k,
            "name": v["name"],
            "fingerprint": v["fingerprint"],
            "sql": v["sql"],
            "table": v["table"],
            "index": v["index"],
            "category": v["category"]
        }
        for k, v in QUERIES.items()
    ]
