"""
Data Quality Tracker and Telemetry Health Monitor
Aggregates telemetry anomalies, pipeline delays, missing sources, and overall health status.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pipeline.deduplicator import deduplicator
from pipeline.ordering import order_manager

class DataQualityTracker:
    def __init__(self):
        self.total_events: int = 0
        self.missing_plan_sources: int = 0
        self.missing_release_sources: int = 0
        self.delayed_index_count: int = 0
        self.stale_statistics_count: int = 0
        self.last_event_time: Optional[str] = None

    def record_event_processed(self, is_duplicate: bool, is_late: bool, is_out_of_order: bool, event_time: Optional[str] = None):
        self.total_events += 1
        if event_time:
            self.last_event_time = event_time

    def record_missing_source(self, source_name: str):
        if source_name == "plan":
            self.missing_plan_sources += 1
        elif source_name == "release":
            self.missing_release_sources += 1
        elif source_name == "index":
            self.delayed_index_count += 1
        elif source_name == "statistics":
            self.stale_statistics_count += 1

    def compute_health_score(self) -> float:
        """
        Calculates an overall data quality health score from 0.0 to 100.0%.
        Penalizes for missing plans, unindexed sources, stale stats, and high late/out-of-order ratios.
        """
        score = 100.0
        
        # Penalties for critical missing upstream sources
        if self.missing_plan_sources > 0:
            score -= min(30.0, self.missing_plan_sources * 10.0)
        if self.missing_release_sources > 0:
            score -= min(15.0, self.missing_release_sources * 5.0)
        if self.delayed_index_count > 0:
            score -= min(15.0, self.delayed_index_count * 5.0)
        if self.stale_statistics_count > 0:
            score -= min(20.0, self.stale_statistics_count * 5.0)

        # Penalties for pipeline jitter
        if self.total_events > 0:
            late_ratio = order_manager.late_events_count / self.total_events
            ooo_ratio = order_manager.out_of_order_count / self.total_events
            score -= min(10.0, late_ratio * 50.0)
            score -= min(10.0, ooo_ratio * 50.0)

        return max(0.0, round(score, 1))

    def get_quality_report(self) -> Dict[str, Any]:
        dedupe_stats = deduplicator.get_stats()
        order_stats = order_manager.get_stats()
        health_score = self.compute_health_score()

        status_label = "Healthy" if health_score >= 85 else ("Degraded" if health_score >= 60 else "Critical")

        return {
            "total_events": self.total_events,
            "duplicates_received": dedupe_stats["duplicates_received"],
            "duplicates_removed": dedupe_stats["duplicates_removed"],
            "late_events_count": order_stats["late_events_count"],
            "out_of_order_count": order_stats["out_of_order_count"],
            "reordered_events_count": order_stats["reordered_events_count"],
            "missing_plan_sources": self.missing_plan_sources,
            "missing_release_sources": self.missing_release_sources,
            "delayed_index_count": self.delayed_index_count,
            "stale_statistics_count": self.stale_statistics_count,
            "overall_health_score": health_score,
            "status": status_label,
            "last_event_time": self.last_event_time or datetime.now(timezone.utc).isoformat(),
            "sources": {
                "query_executions": "Healthy" if self.total_events > 0 else "Pending",
                "plans": "Missing" if self.missing_plan_sources > 0 else "Healthy",
                "indexes": "Delayed" if self.delayed_index_count > 0 else "Healthy",
                "statistics": "Stale" if self.stale_statistics_count > 0 else "Healthy",
                "releases": "Missing" if self.missing_release_sources > 0 else "Healthy"
            }
        }

    def reset(self):
        self.total_events = 0
        self.missing_plan_sources = 0
        self.missing_release_sources = 0
        self.delayed_index_count = 0
        self.stale_statistics_count = 0
        self.last_event_time = None

data_quality_tracker = DataQualityTracker()
