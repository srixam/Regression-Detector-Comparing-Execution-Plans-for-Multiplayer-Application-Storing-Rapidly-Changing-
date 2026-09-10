"""
Tests for Pipeline Deduplication, Event Ordering, and Lateness Handling
"""

import pytest
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.deduplicator import EventDeduplicator
from pipeline.ordering import EventOrderManager
from pipeline.normalizer import EventNormalizer

def test_deduplicator_idempotency():
    dedup = EventDeduplicator(capacity=100)
    
    # Event 1
    assert not dedup.is_duplicate("evt_001", "hash_abc")
    # Event 2
    assert not dedup.is_duplicate("evt_002", "hash_def")
    # Duplicate Event 2
    assert dedup.is_duplicate("evt_002", "hash_def")
    # Event 3
    assert not dedup.is_duplicate("evt_003", "hash_ghi")

    stats = dedup.get_stats()
    assert stats["seen_unique_count"] == 3
    assert stats["duplicates_received"] == 1
    assert stats["duplicates_removed"] == 1

def test_lateness_detection():
    mgr = EventOrderManager(max_allowed_lateness_seconds=60.0)
    now = datetime.now(timezone.utc)

    # Event on time (lag 2 seconds)
    t1 = mgr.check_timing(now.isoformat(), (now + timedelta(seconds=2)).isoformat())
    assert t1["is_late"] is False

    # Event delayed by 120 seconds
    t2 = mgr.check_timing(now.isoformat(), (now + timedelta(seconds=120)).isoformat())
    assert t2["is_late"] is True
    assert mgr.late_events_count == 1

def test_out_of_order_reordering():
    mgr = EventOrderManager()
    now = datetime.now(timezone.utc)

    e1 = {"event_id": "1", "event_time": (now + timedelta(seconds=10)).isoformat()}
    e2 = {"event_id": "2", "event_time": (now + timedelta(seconds=20)).isoformat()}
    e3 = {"event_id": "3", "event_time": (now + timedelta(seconds=30)).isoformat()}

    # Inverted arrival sequence
    shuffled = [e3, e1, e2]
    reordered = mgr.reorder_batch(shuffled)

    assert [e["event_id"] for e in reordered] == ["1", "2", "3"]
