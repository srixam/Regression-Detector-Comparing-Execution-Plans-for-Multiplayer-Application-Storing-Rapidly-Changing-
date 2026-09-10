"""
Detector State Manager
Maintains in-memory and persisted alert registry, recent plan captures, and simulation state.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class DetectorState:
    _instance = None

    def __init__(self):
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.captured_plans: Dict[str, Dict[str, Any]] = {}
        self.simulation_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_alert(self, query_fingerprint: str, alert: Dict[str, Any]):
        self.active_alerts[query_fingerprint] = alert

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return list(self.active_alerts.values())

    def get_alert_by_fingerprint(self, query_fingerprint: str) -> Optional[Dict[str, Any]]:
        return self.active_alerts.get(query_fingerprint)

    def clear_alerts(self):
        self.active_alerts.clear()

    def remove_alert(self, query_fingerprint: str):
        if query_fingerprint in self.active_alerts:
            del self.active_alerts[query_fingerprint]

    def set_plan(self, query_fingerprint: str, plan_json: Dict[str, Any]):
        self.captured_plans[query_fingerprint] = plan_json

    def get_plan(self, query_fingerprint: str) -> Optional[Dict[str, Any]]:
        return self.captured_plans.get(query_fingerprint)

detector_state = DetectorState.get_instance()
