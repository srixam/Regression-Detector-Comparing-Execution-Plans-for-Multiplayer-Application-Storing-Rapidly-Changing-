-- QueryGuard PostgreSQL Schema
-- Database schema for multiplayer session state, execution telemetry, and regression detection

CREATE TABLE IF NOT EXISTS players (
    player_id VARCHAR(64) PRIMARY KEY,
    region VARCHAR(32) NOT NULL,
    skill_rating INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS game_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    game_id VARCHAR(64) NOT NULL,
    player_id VARCHAR(64) NOT NULL REFERENCES players(player_id),
    server_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL, -- 'active', 'completed', 'abandoned'
    region VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS game_events (
    event_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    player_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB,
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS servers (
    server_id VARCHAR(64) PRIMARY KEY,
    region VARCHAR(32) NOT NULL,
    active_players INT NOT NULL DEFAULT 0,
    cpu_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    memory_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS query_executions (
    execution_id VARCHAR(64) PRIMARY KEY,
    event_id VARCHAR(64),
    query_fingerprint VARCHAR(128) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    rows_returned INT NOT NULL DEFAULT 0,
    plan_hash VARCHAR(64),
    release_id VARCHAR(64),
    workload_level DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS query_plans (
    plan_id VARCHAR(64) PRIMARY KEY,
    query_fingerprint VARCHAR(128) NOT NULL,
    plan_hash VARCHAR(64) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    plan_json JSONB NOT NULL,
    source_status VARCHAR(32) NOT NULL DEFAULT 'available' -- 'available', 'unavailable', 'corrupted'
);

CREATE TABLE IF NOT EXISTS indexes (
    index_name VARCHAR(128) PRIMARY KEY,
    table_name VARCHAR(128) NOT NULL,
    columns TEXT NOT NULL,
    status VARCHAR(32) NOT NULL, -- 'active', 'missing', 'invalid', 'delayed'
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS statistics_snapshots (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(128) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_count BIGINT NOT NULL DEFAULT 0,
    dead_tuples BIGINT NOT NULL DEFAULT 0,
    last_analyze TIMESTAMPTZ,
    estimated_rows BIGINT NOT NULL DEFAULT 0,
    actual_rows BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS releases (
    release_id VARCHAR(64) PRIMARY KEY,
    version VARCHAR(32) NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL,
    description TEXT,
    schema_change BOOLEAN NOT NULL DEFAULT FALSE,
    index_change BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS normalized_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL,
    processing_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence_number BIGINT NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    is_out_of_order BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS query_baselines (
    query_fingerprint VARCHAR(128) PRIMARY KEY,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    baseline_p50 DOUBLE PRECISION NOT NULL,
    baseline_p95 DOUBLE PRECISION NOT NULL,
    baseline_p99 DOUBLE PRECISION NOT NULL,
    std_latency DOUBLE PRECISION NOT NULL,
    execution_count INT NOT NULL,
    baseline_plan_hash VARCHAR(64),
    baseline_plan_type VARCHAR(64),
    estimated_rows DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    actual_rows DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    index_used VARCHAR(128),
    statistics_age_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    workload_level DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS regression_alerts (
    regression_id VARCHAR(64) PRIMARY KEY,
    query_fingerprint VARCHAR(128) NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    severity VARCHAR(32) NOT NULL, -- 'NORMAL', 'WARNING', 'HIGH', 'CRITICAL'
    regression_score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    baseline_p50 DOUBLE PRECISION NOT NULL,
    baseline_p95 DOUBLE PRECISION NOT NULL,
    baseline_p99 DOUBLE PRECISION NOT NULL,
    current_p50 DOUBLE PRECISION NOT NULL,
    current_p95 DOUBLE PRECISION NOT NULL,
    current_p99 DOUBLE PRECISION NOT NULL,
    latency_change_pct DOUBLE PRECISION NOT NULL,
    plan_changed BOOLEAN NOT NULL,
    index_changed BOOLEAN NOT NULL,
    statistics_changed BOOLEAN NOT NULL,
    workload_changed BOOLEAN NOT NULL,
    release_correlated BOOLEAN NOT NULL,
    root_cause TEXT NOT NULL,
    evidence_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS ground_truth (
    scenario_id VARCHAR(64) PRIMARY KEY,
    query_fingerprint VARCHAR(128) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    scenario VARCHAR(64) NOT NULL,
    is_regression BOOLEAN NOT NULL,
    expected_severity VARCHAR(32) NOT NULL,
    expected_root_cause VARCHAR(64) NOT NULL
);

-- Essential Performance Indexes
CREATE INDEX IF NOT EXISTS idx_player_session ON game_sessions(player_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_server_status ON game_sessions(server_id, status);
CREATE INDEX IF NOT EXISTS idx_players_region_skill ON players(region, skill_rating DESC);
CREATE INDEX IF NOT EXISTS idx_game_events_session_time ON game_events(session_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_query_exec_fp_time ON query_executions(query_fingerprint, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_detected ON regression_alerts(detected_at DESC);
