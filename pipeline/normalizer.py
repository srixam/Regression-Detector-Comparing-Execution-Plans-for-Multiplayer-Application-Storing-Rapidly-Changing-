"""
Event Normalization Pipeline
Validates, deduplicates, tags, hashes, and sequences incoming events.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pipeline.deduplicator import deduplicator
from pipeline.ordering import order_manager

class EventNormalizer:
    def __init__(self):
        self.sequence_counter: int = 0

    def compute_payload_hash(self, payload: Any) -> str:
        if isinstance(payload, dict):
            raw = json.dumps(payload, sort_keys=True)
        elif isinstance(payload, str):
            raw = payload
        else:
            raw = str(payload)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def normalize_event(self, raw_event: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Processes a single raw event.
        Returns (normalized_event_dict, is_duplicate).
        If duplicate, is_duplicate=True and normalized_event_dict will have is_duplicate=True.
        """
        event_id = raw_event.get("event_id") or raw_event.get("execution_id") or f"gen-{self.sequence_counter}"
        event_type = raw_event.get("event_type", "query_execution")
        
        # Parse or default timestamps
        event_time = raw_event.get("event_time") or datetime.now(timezone.utc).isoformat()
        ingestion_time = raw_event.get("ingestion_time") or datetime.now(timezone.utc).isoformat()
        processing_time = datetime.now(timezone.utc).isoformat()

        payload = raw_event.get("payload", raw_event)
        payload_hash = self.compute_payload_hash(payload)

        # 1. Deduplication check
        is_dupe = deduplicator.is_duplicate(event_id, payload_hash)

        # 2. Timing check
        timing = order_manager.check_timing(event_time, ingestion_time)

        self.sequence_counter += 1

        normalized = {
            "event_id": event_id,
            "event_type": event_type,
            "event_time": event_time,
            "ingestion_time": ingestion_time,
            "processing_time": processing_time,
            "sequence_number": self.sequence_counter,
            "payload_hash": payload_hash,
            "is_duplicate": is_dupe,
            "is_late": timing["is_late"],
            "is_out_of_order": timing["is_out_of_order"],
            "raw_payload": raw_event
        }

        return normalized, is_dupe

    def normalize_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch processing with ordering and deduplication.
        Drops duplicates from execution analytics while recording their metadata.
        """
        # Reorder first to reconstruct correct chronological order
        reordered = order_manager.reorder_batch(events)
        
        valid_normalized = []
        for raw in reordered:
            norm, is_dupe = self.normalize_event(raw)
            if not is_dupe:
                valid_normalized.append(norm)

        return valid_normalized

    def reset(self):
        self.sequence_counter = 0
        deduplicator.reset()
        order_manager.reset()

normalizer = EventNormalizer()
