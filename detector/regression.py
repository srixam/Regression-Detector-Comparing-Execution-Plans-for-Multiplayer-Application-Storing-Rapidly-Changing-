"""
Regression Detector Orchestrator
Coordinates features, baseline comparison, plan diffs, hybrid scoring, evidence generation,
and alert dispatching.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from detector.baseline import baseline_engine
from detector.plan_comparator import plan_comparator
from detector.scoring import scorer
from detector.evidence import evidence_engine
from detector.root_cause import root_cause_engine
from simulator.release_generator import release_tracker
from simulator.query_generator import get_query_meta
from database.connection import db
from backend.models.domain import Severity

class RegressionDetector:
    def __init__(self):
        self._active_alerts: Dict[str, Dict[str, Any]] = {}
        self._persistence_tracker: Dict[str, int] = {}
        self.early_warning_metrics: Dict[str, Any] = {
            "early_warning_seconds": 60.0,
            "detection_time": None,
            "user_impact_time": None
        }

    def evaluate_query(
        self,
        query_fingerprint: str,
        features: Dict[str, Any],
        current_plan_json: Optional[Dict[str, Any]] = None,
        baseline_plan_json: Optional[Dict[str, Any]] = None,
        detected_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end regression evaluation for a specific query fingerprint.
        """
        dt = detected_at or datetime.now(timezone.utc)
        baseline = baseline_engine.get_baseline(query_fingerprint)
        if not baseline:
            # Generate ad-hoc baseline if none recorded yet
            from simulator.query_generator import FINGERPRINT_TO_KEY
            q_key = FINGERPRINT_TO_KEY.get(query_fingerprint, "get_active_player_session")
            from simulator.workload_generator import workload_gen
            execs = workload_gen.generate_executions(count=50, mode="normal", regressed_query_key=q_key)
            filtered = [e for e in execs if e["query_fingerprint"] == query_fingerprint]
            baseline = baseline_engine.calculate_baseline_from_executions(query_fingerprint, filtered)

        # 1. Compare Execution Plans
        if features.get("has_plan_source", True) and current_plan_json and baseline_plan_json:
            plan_diff = plan_comparator.compare_plans(baseline_plan_json, current_plan_json)
        else:
            plan_diff = {
                "plan_changed": False,
                "is_significant_regression": False,
                "plan_score_penalty": 0.0,
                "diff_summary": "Plan Telemetry Unavailable",
                "human_readable_diff": "N/A (Missing plan)",
                "cost_change_pct": 0.0,
                "baseline_metrics": {},
                "current_metrics": {}
            }

        # 2. Track Persistence
        b_p95 = max(float(baseline.get("baseline_p95", 25.0)), 0.1)
        c_p95 = float(features.get("p95", 25.0))
        lat_change_pct = ((c_p95 - b_p95) / b_p95) * 100.0

        if lat_change_pct >= 20.0:
            self._persistence_tracker[query_fingerprint] = self._persistence_tracker.get(query_fingerprint, 0) + 1
        else:
            self._persistence_tracker[query_fingerprint] = 0

        persistence_count = self._persistence_tracker.get(query_fingerprint, 1)

        # 3. Check Release Correlation
        release_details = release_tracker.correlate_with_regression(dt)

        # 4. Hybrid Scoring
        score_result = scorer.compute_score(baseline, features, plan_diff, persistence_count)
        severity = score_result["severity"]
        reg_score = score_result["regression_score"]
        confidence = score_result["confidence"]

        # 5. Query Details
        try:
            q_meta = get_query_meta(query_fingerprint)
            q_name = q_meta["name"]
        except Exception:
            q_name = query_fingerprint

        # 6. Generate Factual Evidence
        evidence_items = evidence_engine.generate_evidence(
            q_name, baseline, features, plan_diff, score_result, release_details
        )

        # 7. Classify Root Cause
        root_cause_str, rc_confidence = root_cause_engine.determine_root_cause(
            features, plan_diff, score_result, release_details
        )

        # Overall confidence is harmonic mean of scoring confidence & root cause confidence
        final_confidence = round((confidence * 0.6) + (rc_confidence * 0.4), 2)

        # 8. Create Alert Object
        alert_id = f"reg-{uuid.uuid4().hex[:10]}"
        alert = {
            "regression_id": alert_id,
            "query_fingerprint": query_fingerprint,
            "query_name": q_name,
            "detected_at": dt.isoformat(),
            "severity": severity.value,
            "regression_score": reg_score,
            "confidence": final_confidence,
            "baseline_p50": baseline["baseline_p50"],
            "baseline_p95": baseline["baseline_p95"],
            "baseline_p99": baseline["baseline_p99"],
            "current_p50": features.get("p50", 0.0),
            "current_p95": features.get("p95", 0.0),
            "current_p99": features.get("p99", 0.0),
            "latency_change_pct": score_result["latency_change_pct"],
            "plan_changed": plan_diff["plan_changed"],
            "index_changed": (features.get("index_status") != "active"),
            "statistics_changed": (features.get("cardinality_error", 0.0) >= 2.0),
            "workload_changed": (features.get("workload_level", 1.0) > 2.0),
            "release_correlated": (release_details is not None and release_details.get("is_correlated", False)),
            "root_cause": root_cause_str,
            "evidence_json": {
                "items": evidence_items,
                "plan_diff": plan_diff.get("human_readable_diff", ""),
                "diff_summary": plan_diff.get("diff_summary", ""),
                "subscores": score_result.get("subscores", {}),
                "release": release_details
            }
        }

        # Store alert if severity is WARNING, HIGH, or CRITICAL
        if severity != Severity.NORMAL:
            self._active_alerts[query_fingerprint] = alert
            self.persist_alert(alert)

        return alert

    def persist_alert(self, alert: Dict[str, Any]) -> None:
        import json
        try:
            sql = """
            INSERT INTO regression_alerts (
                regression_id, query_fingerprint, detected_at, severity, regression_score,
                confidence, baseline_p50, baseline_p95, baseline_p99, current_p50, current_p95,
                current_p99, latency_change_pct, plan_changed, index_changed, statistics_changed,
                workload_changed, release_correlated, root_cause, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (regression_id) DO NOTHING;
            """
            params = (
                alert["regression_id"],
                alert["query_fingerprint"],
                alert["detected_at"],
                alert["severity"],
                alert["regression_score"],
                alert["confidence"],
                alert["baseline_p50"],
                alert["baseline_p95"],
                alert["baseline_p99"],
                alert["current_p50"],
                alert["current_p95"],
                alert["current_p99"],
                alert["latency_change_pct"],
                alert["plan_changed"],
                alert["index_changed"],
                alert["statistics_changed"],
                alert["workload_changed"],
                alert["release_correlated"],
                alert["root_cause"],
                json.dumps(alert["evidence_json"])
            )
            db.execute(sql, params)
        except Exception:
            pass

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return list(self._active_alerts.values())

    def clear_alerts(self) -> None:
        self._active_alerts.clear()
        self._persistence_tracker.clear()

detector = RegressionDetector()
