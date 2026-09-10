"""
Fault and Reliability Failure Injector
Supports controlled, reproducible injection of:
- Duplicate events
- Delayed events
- Out-of-order events
- Missing query-plan source
- Missing release source
- Delayed index metadata
- Stale catalog statistics
- Removed index
- Workload spikes
"""

import copy
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

class FaultInjector:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def inject_duplicates(self, events: List[Dict[str, Any]], duplicate_ratio: float = 0.2) -> List[Dict[str, Any]]:
        """Injects duplicate copies of existing events into the stream."""
        result = list(events)
        num_dupes = int(len(events) * duplicate_ratio)
        if not events or num_dupes == 0:
            return result
        
        candidates = self.rng.sample(events, min(num_dupes, len(events)))
        for item in candidates:
            dupe = copy.deepcopy(item)
            # Insert at a randomized later point
            insert_idx = self.rng.randint(0, len(result))
            result.insert(insert_idx, dupe)
            
        return result

    def inject_delayed_events(self, events: List[Dict[str, Any]], delay_seconds: float = 45.0, delay_ratio: float = 0.3) -> List[Dict[str, Any]]:
        """Modifies ingestion_time so that events arrive significantly later than event_time."""
        result = copy.deepcopy(events)
        num_delayed = int(len(result) * delay_ratio)
        if not result or num_delayed == 0:
            return result

        candidates = self.rng.sample(result, min(num_delayed, len(result)))
        for item in candidates:
            try:
                evt_dt = datetime.fromisoformat(item["event_time"])
                delayed_ingest = evt_dt + timedelta(seconds=delay_seconds + self.rng.uniform(5.0, 20.0))
                item["ingestion_time"] = delayed_ingest.isoformat()
                item["_injected_delay"] = True
            except Exception:
                pass
                
        return result

    def inject_out_of_order(self, events: List[Dict[str, Any]], shuffle_ratio: float = 0.4) -> List[Dict[str, Any]]:
        """Shuffles a subset of events in the stream so arrival order diverges from chronological event_time."""
        result = copy.deepcopy(events)
        if len(result) < 3:
            return result

        # Split into blocks and randomly swap chunks or shuffle windows
        window_size = 5
        for i in range(0, len(result) - window_size, window_size):
            if self.rng.random() < shuffle_ratio:
                sub = result[i:i + window_size]
                self.rng.shuffle(sub)
                result[i:i + window_size] = sub

        return result

    def simulate_missing_plan_source(self, plan_json: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates plan source outage or unreachable catalog."""
        return {
            "Plan": {},
            "source_status": "unavailable",
            "error": "Query plan telemetry provider timeout or missing EXPLAIN source"
        }

    def simulate_delayed_index_metadata(self) -> Dict[str, Any]:
        """Simulates index metadata delay."""
        return {
            "index_name": "idx_player_session",
            "table_name": "game_sessions",
            "columns": "player_id, status",
            "status": "delayed",
            "captured_at": datetime.now(timezone.utc).isoformat()
        }

    def simulate_stale_statistics(self, table_name: str = "game_sessions") -> Dict[str, Any]:
        """Simulates severely outdated optimizer statistics with huge cardinality disparity."""
        return {
            "table_name": table_name,
            "captured_at": (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat(),
            "row_count": 1500,
            "dead_tuples": 12400,
            "last_analyze": (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat(),
            "estimated_rows": 100,
            "actual_rows": 45000,
            "cardinality_error": 449.0
        }

fault_injector = FaultInjector()
