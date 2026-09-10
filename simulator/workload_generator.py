"""
Multiplayer Workload Generator
Simulates realistic query execution streams, query durations, concurrency levels,
and performance transitions under normal and stress conditions.
"""

import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from simulator.query_generator import QUERIES, KEY_TO_FINGERPRINT
from simulator.plan_generator import get_baseline_plan, get_regressed_plan, extract_plan_metrics

# Healthy baseline latency distributions (mean, std in ms)
BASE_LATENCIES = {
    "get_active_player_session": (24.0, 5.0),
    "update_session_state": (12.0, 3.0),
    "get_recent_game_events": (35.0, 8.0),
    "region_leaderboard": (48.0, 10.0),
    "get_active_sessions_on_server": (42.0, 9.0),
    "get_player_profile": (18.0, 4.0),
    "get_active_players_by_region": (65.0, 12.0)
}

class WorkloadGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_executions(
        self,
        count: int = 100,
        mode: str = "normal",
        start_time: Optional[datetime] = None,
        duration_window_seconds: int = 60,
        regressed_query_key: str = "get_active_player_session"
    ) -> List[Dict[str, Any]]:
        """
        Generates realistic query execution telemetry.
        Modes:
          - 'normal': baseline healthy latency across all queries (~800 queries/min rate)
          - 'index_regression': regressed_query has high latency (180-220ms) and Seq Scan plan
          - 'statistics_regression': cardinality mismatch and 200-260ms latency
          - 'workload_spike': 10x traffic volume, higher latency (120-160ms) but plans remain unchanged!
          - 'early_warning': progressive drift from 0s to duration_window_seconds
        """
        t_start = start_time or (datetime.now(timezone.utc) - timedelta(seconds=duration_window_seconds))
        executions = []
        
        query_keys = list(QUERIES.keys())
        # Weighted selection: session state read and update dominate multiplayer game loop
        weights = [35, 25, 15, 8, 7, 6, 4]

        # Extract plan hashes for baseline and regressed
        baseline_plan = get_baseline_plan(regressed_query_key)
        baseline_meta = extract_plan_metrics(baseline_plan)
        
        seq_plan = get_regressed_plan(regressed_query_key, scenario="index_removed")
        seq_meta = extract_plan_metrics(seq_plan)

        drift_plan = get_regressed_plan(regressed_query_key, scenario="early_warning_drift")
        drift_meta = extract_plan_metrics(drift_plan)

        stale_plan = get_regressed_plan(regressed_query_key, scenario="stale_statistics")
        stale_meta = extract_plan_metrics(stale_plan)

        for i in range(count):
            q_key = self.rng.choices(query_keys, weights=weights)[0]
            fp = KEY_TO_FINGERPRINT[q_key]
            
            # Timestamp spaced evenly through the window
            fraction = i / max(count, 1)
            event_dt = t_start + timedelta(seconds=fraction * duration_window_seconds)
            ingest_dt = event_dt + timedelta(milliseconds=self.rng.uniform(5, 25))

            mean_lat, std_lat = BASE_LATENCIES.get(q_key, (25.0, 5.0))
            duration = max(2.0, self.rng.gauss(mean_lat, std_lat))
            plan_hash = baseline_meta["plan_hash"]
            workload_lvl = 1.0

            if mode == "index_regression" and q_key == regressed_query_key:
                duration = self.rng.gauss(192.0, 15.0)  # ~192ms
                plan_hash = seq_meta["plan_hash"]
                workload_lvl = 1.0

            elif mode == "statistics_regression" and q_key == regressed_query_key:
                duration = self.rng.gauss(245.0, 22.0)  # ~245ms
                plan_hash = stale_meta["plan_hash"]
                workload_lvl = 1.0

            elif mode == "workload_spike":
                # High concurrency causes wait queueing, latency goes up 3x-4x, but plan remains identical!
                workload_lvl = 10.0
                duration = duration * self.rng.uniform(3.0, 4.5)
                plan_hash = baseline_meta["plan_hash"]

            elif mode == "early_warning" and q_key == regressed_query_key:
                # Timeline progression:
                # 0% - 25%: normal (24ms)
                # 25% - 50%: cardinality begins drifting (32ms, drift plan)
                # 50% - 75%: plan cost rises, latency begins increasing (75ms)
                # 75% - 100%: user impact threshold exceeded (190ms)
                if fraction < 0.25:
                    duration = self.rng.gauss(24.0, 4.0)
                    plan_hash = baseline_meta["plan_hash"]
                elif fraction < 0.50:
                    duration = self.rng.gauss(38.0, 6.0)
                    plan_hash = drift_meta["plan_hash"]
                elif fraction < 0.75:
                    duration = self.rng.gauss(85.0, 10.0)
                    plan_hash = drift_meta["plan_hash"]
                else:
                    duration = self.rng.gauss(195.0, 20.0)
                    plan_hash = seq_meta["plan_hash"]

            executions.append({
                "execution_id": f"exec-{uuid.uuid4().hex[:12]}",
                "event_id": f"evt-{uuid.uuid4().hex[:12]}",
                "query_fingerprint": fp,
                "query_key": q_key,
                "event_time": event_dt.isoformat(),
                "ingestion_time": ingest_dt.isoformat(),
                "duration_ms": round(duration, 3),
                "rows_returned": 1 if "session" in q_key or "profile" in q_key else self.rng.randint(10, 100),
                "plan_hash": plan_hash,
                "release_id": "rel-v2.3.1" if mode in ["index_regression", "early_warning"] else "rel-v2.3.0",
                "workload_level": workload_lvl
            })

        return executions

workload_gen = WorkloadGenerator()
