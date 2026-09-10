"""
API Schemas for QueryGuard Requests and Responses
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from backend.models.domain import Severity, RegressionAlert, QueryBaseline, DataQualityReport

class OverviewMetrics(BaseModel):
    total_queries_monitored: int
    critical_regressions: int
    high_regressions: int
    warnings: int
    avg_p95_latency_ms: float
    detection_latency_seconds: float
    early_warning_seconds: float
    data_source_health: Dict[str, str]
    overall_status: str

class QuerySummary(BaseModel):
    query_fingerprint: str
    query_name: str
    sql_template: str
    baseline_p95_ms: float
    current_p95_ms: float
    latency_delta_pct: float
    status: Severity
    last_detected_at: Optional[datetime] = None

class PlanComparisonResponse(BaseModel):
    query_fingerprint: str
    baseline_plan_hash: Optional[str]
    current_plan_hash: Optional[str]
    plan_changed: bool
    structural_diff: str
    baseline_node_type: Optional[str]
    current_node_type: Optional[str]
    baseline_total_cost: float
    current_total_cost: float
    cost_change_pct: float
    baseline_plan_json: Optional[Dict[str, Any]] = None
    current_plan_json: Optional[Dict[str, Any]] = None

class EventBatchRequest(BaseModel):
    events: List[Dict[str, Any]]

class SimulationStartRequest(BaseModel):
    scenario_name: str
    target_query: Optional[str] = None
    duration_seconds: int = 60
    random_seed: int = 42

class SimulationResponse(BaseModel):
    scenario_name: str
    status: str
    events_generated: int
    events_processed: int
    regressions_detected: int
    recovery_status: str
    details: Dict[str, Any]

class EvaluationMetricsResponse(BaseModel):
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float
    detection_latency_seconds: float
    early_warning_seconds: float
    duplicate_recovery_rate: float
    late_event_recovery_rate: float
    out_of_order_recovery_rate: float
    confusion_matrix: Dict[str, int]
    scenarios_evaluated: List[Dict[str, Any]]
    false_positive_details: List[Dict[str, Any]]
    false_negative_details: List[Dict[str, Any]]
    target_vs_measured: List[Dict[str, Any]]
