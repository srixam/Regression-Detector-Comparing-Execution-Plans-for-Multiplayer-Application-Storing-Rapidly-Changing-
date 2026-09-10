"""
Release History Generator and Correlation Engine
Tracks deployments, schema migrations, and index alterations, computing
temporal deltas between code releases and observed performance regressions.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid

DEFAULT_RELEASES = [
    {
        "release_id": "rel-v2.2.0",
        "version": "v2.2.0",
        "deployed_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "description": "Multiplayer matchmaking and lobby routing optimization",
        "schema_change": False,
        "index_change": False
    },
    {
        "release_id": "rel-v2.3.0",
        "version": "v2.3.0",
        "deployed_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "description": "Cross-region game event streaming improvements",
        "schema_change": False,
        "index_change": False
    },
    {
        "release_id": "rel-v2.3.1",
        "version": "v2.3.1",
        "deployed_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
        "description": "Session table partition restructuring and index cleanup",
        "schema_change": True,
        "index_change": True
    }
]

class ReleaseTracker:
    def __init__(self, releases: Optional[List[Dict[str, Any]]] = None):
        self.releases = releases or [r.copy() for r in DEFAULT_RELEASES]

    def add_release(self, version: str, description: str, schema_change: bool = False, index_change: bool = False, deployed_at: Optional[datetime] = None) -> Dict[str, Any]:
        dt = deployed_at or datetime.now(timezone.utc)
        rel = {
            "release_id": f"rel-{version}",
            "version": version,
            "deployed_at": dt.isoformat(),
            "description": description,
            "schema_change": schema_change,
            "index_change": index_change
        }
        self.releases.append(rel)
        return rel

    def get_all_releases(self) -> List[Dict[str, Any]]:
        # Sort by deployed_at descending
        return sorted(self.releases, key=lambda x: x["deployed_at"], reverse=True)

    def correlate_with_regression(self, detected_at: datetime, max_window_minutes: int = 120) -> Optional[Dict[str, Any]]:
        """
        Looks for the most recent release deployed prior to detected_at.
        Returns correlation details and formatted delta string.
        """
        if not self.releases:
            return None

        candidates = []
        for r in self.releases:
            try:
                deployed_time = datetime.fromisoformat(r["deployed_at"])
                if deployed_time.tzinfo is None:
                    deployed_time = deployed_time.replace(tzinfo=timezone.utc)
                if detected_at.tzinfo is None:
                    detected_at = detected_at.replace(tzinfo=timezone.utc)
                    
                delta = detected_at - deployed_time
                if timedelta(seconds=0) <= delta <= timedelta(minutes=max_window_minutes):
                    candidates.append((delta.total_seconds(), r))
            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        best_delta_sec, best_release = candidates[0]
        
        minutes = int(best_delta_sec // 60)
        seconds = int(best_delta_sec % 60)
        formatted_delta = f"{minutes}m {seconds}s"

        return {
            "release_id": best_release["release_id"],
            "version": best_release["version"],
            "deployed_at": best_release["deployed_at"],
            "description": best_release["description"],
            "schema_change": best_release["schema_change"],
            "index_change": best_release["index_change"],
            "time_from_release_to_regression_seconds": best_delta_sec,
            "formatted_delta": formatted_delta,
            "is_correlated": True,
            "statement": f"Strong temporal correlation with release {best_release['version']} ({formatted_delta} before detection)"
        }

release_tracker = ReleaseTracker()
