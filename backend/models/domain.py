"""
Domain Models for QueryGuard
Defines core data classes and structures for telemetry, executions, plans, alerts, and baselines.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RootCause(str, Enum):
    MISSING_INDEX = "Missing index after schema deployment"
    STALE_STATISTICS = "Stale optimizer statistics or altered data distribution"
    WORKLOAD_SPIKE = "High query concurrency / workload surge"
    RELEASE_REGRESSION = "Release-correlated query regression"
    NORMAL_VARIATION = "Normal operational latency jitter"
    DATA_QUALITY_DEGRADATION = "Degraded telemetry or missing plan sources"

class Player(BaseModel):
    player_id: str
    region: str
    skill_rating: int
    created_at: datetime

class GameSession(BaseModel):
    session_id: str
    game_id: str
    player_id: str
    server_id: str
    status: str
    region: str
    started_at: datetime
    updated_at: datetime

class GameEvent(BaseModel):
    event_id: str
    session_id: str
    player_id: str
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    event_time: datetime

class Server(BaseModel):
    server_id: str
    region: str
    active_players: int
    cpu_percent: float
    memory_percent: float
    recorded_at: datetime

class QueryExecution(BaseModel):
    execution_id: str
    event_id: Optional[str] = None
    query_fingerprint: str
    event_time: datetime
    ingestion_time: datetime
    duration_ms: float
    rows_returned: int = 0
    plan_hash: Optional[str] = None
    release_id: Optional[str] = None
    workload_level: float = 1.0

class QueryPlan(BaseModel):
    plan_id: str
    query_fingerprint: str
    plan_hash: str
    captured_at: datetime
    plan_json: Dict[str, Any]
    source_status: str = "available"  # 'available', 'unavailable', 'corrupted'

class IndexMetadata(BaseModel):
    index_name: str
    table_name: str
    columns: str
    status: str  # 'active', 'missing', 'invalid', 'delayed'
    captured_at: datetime

class StatisticsSnapshot(BaseModel):
    id: Optional[int] = None
    table_name: str
    captured_at: datetime
    row_count: int
    dead_tuples: int
    last_analyze: Optional[datetime] = None
    estimated_rows: int
    actual_rows: int

class Release(BaseModel):
    release_id: str
    version: str
    deployed_at: datetime
    description: Optional[str] = None
    schema_change: bool = False
    index_change: bool = False

class NormalizedEvent(BaseModel):
    event_id: str
    event_type: str
    event_time: datetime
    ingestion_time: datetime
    processing_time: datetime
    sequence_number: int
    payload_hash: str
    is_duplicate: bool = False
    is_late: bool = False
    is_out_of_order: bool = False

class QueryBaseline(BaseModel):
    query_fingerprint: str
    calculated_at: datetime
    baseline_p50: float
    baseline_p95: float
    baseline_p99: float
    std_latency: float
    execution_count: int
    baseline_plan_hash: Optional[str] = None
    baseline_plan_type: Optional[str] = None
    estimated_rows: float = 1.0
    actual_rows: float = 1.0
    index_used: Optional[str] = None
    statistics_age_hours: float = 0.0
    workload_level: float = 1.0

class RegressionAlert(BaseModel):
    regression_id: str
    query_fingerprint: str
    detected_at: datetime
    severity: Severity
    regression_score: float
    confidence: float
    baseline_p50: float
    baseline_p95: float
    baseline_p99: float
    current_p50: float
    current_p95: float
    current_p99: float
    latency_change_pct: float
    plan_changed: bool
    index_changed: bool
    statistics_changed: bool
    workload_changed: bool
    release_correlated: bool
    root_cause: str
    evidence_json: Dict[str, Any]

class GroundTruth(BaseModel):
    scenario_id: str
    query_fingerprint: str
    event_time: datetime
    scenario: str
    is_regression: bool
    expected_severity: Severity
    expected_root_cause: str

class DataQualityReport(BaseModel):
    total_events: int = 0
    duplicates_received: int = 0
    duplicates_removed: int = 0
    late_events_count: int = 0
    out_of_order_count: int = 0
    missing_plan_sources: int = 0
    missing_release_sources: int = 0
    delayed_index_count: int = 0
    stale_statistics_count: int = 0
    overall_health_score: float = 100.0
    last_event_time: Optional[datetime] = None
