"""
Event Ordering & Lateness Handling
Uses event_time for chronological timeline analysis.
Maintains a reordering buffer and tracks out-of-order and late events against configurable lateness thresholds.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import heapq

class EventOrderManager:
    def __init__(self, max_allowed_lateness_seconds: float = 60.0, buffer_window_seconds: float = 5.0):
        self.max_allowed_lateness_seconds = max_allowed_lateness_seconds
        self.buffer_window_seconds = buffer_window_seconds
        self.last_event_time: Optional[datetime] = None
        self.out_of_order_count: int = 0
        self.late_events_count: int = 0
        self.reordered_events_count: int = 0

    def parse_datetime(self, dt_val: Any) -> datetime:
        if isinstance(dt_val, datetime):
            if dt_val.tzinfo is None:
                return dt_val.replace(tzinfo=timezone.utc)
            return dt_val
        parsed = datetime.fromisoformat(str(dt_val))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def check_timing(self, event_time_val: Any, ingestion_time_val: Any) -> Dict[str, bool]:
        """
        Evaluates whether an event is late or arrived out of order.
        """
        evt_dt = self.parse_datetime(event_time_val)
        ingest_dt = self.parse_datetime(ingestion_time_val)

        # Calculate arrival lag
        lag_seconds = (ingest_dt - evt_dt).total_seconds()
        is_late = lag_seconds > self.max_allowed_lateness_seconds
        if is_late:
            self.late_events_count += 1

        # Check chronological order relative to last seen event_time
        is_out_of_order = False
        if self.last_event_time is not None:
            if evt_dt < self.last_event_time:
                is_out_of_order = True
                self.out_of_order_count += 1
            else:
                self.last_event_time = evt_dt
        else:
            self.last_event_time = evt_dt

        return {
            "is_late": is_late,
            "is_out_of_order": is_out_of_order,
            "lag_seconds": lag_seconds
        }

    def reorder_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reconstructs the true chronological sequence of events by sorting on event_time.
        """
        def sort_key(item: Dict[str, Any]):
            evt_t = item.get("event_time")
            try:
                return self.parse_datetime(evt_t)
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)

        sorted_events = sorted(events, key=sort_key)
        self.reordered_events_count += len(events)
        return sorted_events

    def get_stats(self) -> Dict[str, Any]:
        return {
            "out_of_order_count": self.out_of_order_count,
            "late_events_count": self.late_events_count,
            "reordered_events_count": self.reordered_events_count,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None
        }

    def reset(self):
        self.last_event_time = None
        self.out_of_order_count = 0
        self.late_events_count = 0
        self.reordered_events_count = 0

order_manager = EventOrderManager()
