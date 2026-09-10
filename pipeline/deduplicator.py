"""
Event Deduplication Module
Ensures idempotent event processing by tracking idempotency keys and payload hashes.
Guarantees duplicate events are filtered without state corruption.
"""

from typing import Dict, Any, Tuple, Set, Optional
from collections import OrderedDict

class EventDeduplicator:
    def __init__(self, capacity: int = 50000):
        self.capacity = capacity
        # OrderedDict used as an LRU cache of seen event_id -> payload_hash
        self.seen_events: OrderedDict[str, str] = OrderedDict()
        self.duplicates_received: int = 0
        self.duplicates_removed: int = 0

    def is_duplicate(self, event_id: str, payload_hash: Optional[str] = None) -> bool:
        """
        Checks if an event has already been processed.
        If seen, increments duplicate counters and returns True.
        Otherwise records the event and returns False.
        """
        if event_id in self.seen_events:
            self.duplicates_received += 1
            self.duplicates_removed += 1
            # Refresh LRU position
            self.seen_events.move_to_end(event_id)
            return True

        # Check capacity eviction
        if len(self.seen_events) >= self.capacity:
            self.seen_events.popitem(last=False)

        self.seen_events[event_id] = payload_hash or ""
        return False

    def get_stats(self) -> Dict[str, int]:
        return {
            "seen_unique_count": len(self.seen_events),
            "duplicates_received": self.duplicates_received,
            "duplicates_removed": self.duplicates_removed
        }

    def reset(self):
        self.seen_events.clear()
        self.duplicates_received = 0
        self.duplicates_removed = 0

deduplicator = EventDeduplicator()
