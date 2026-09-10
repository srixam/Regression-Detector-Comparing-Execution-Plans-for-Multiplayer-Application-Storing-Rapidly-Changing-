-- QueryGuard Seed Data Generation (PostgreSQL)
-- Generates realistic synthetic distributions:
-- 10,000+ players (Gaussian/Zipf-like skill rating distributions across regions)
-- 1,000+ sessions (Active, completed, abandoned)
-- 100,000+ game events (player movements, abilities, heartbeats, state syncs)

-- Clean existing data
TRUNCATE TABLE game_events, game_sessions, players, servers, indexes, releases CASCADE;

-- 1. Insert Servers
INSERT INTO servers (server_id, region, active_players, cpu_percent, memory_percent, recorded_at)
VALUES 
    ('srv-na-01', 'us-east', 2450, 48.5, 62.1, NOW()),
    ('srv-na-02', 'us-west', 1890, 41.2, 55.4, NOW()),
    ('srv-eu-01', 'eu-central', 3120, 68.4, 74.2, NOW()),
    ('srv-eu-02', 'eu-west', 2200, 45.0, 59.8, NOW()),
    ('srv-ap-01', 'ap-southeast', 1980, 52.3, 61.0, NOW()),
    ('srv-ap-02', 'ap-northeast', 2850, 64.1, 70.5, NOW());

-- 2. Generate 10,000 Players with realistic skill ratings (Gaussian around 1500, std 300)
INSERT INTO players (player_id, region, skill_rating, created_at)
SELECT
    'ply-' || LPAD(s.id::text, 6, '0'),
    (ARRAY['us-east', 'us-west', 'eu-central', 'eu-west', 'ap-southeast', 'ap-northeast'])[(s.id % 6) + 1],
    GREATEST(100, LEAST(3000, CAST(1500 + 300 * (
        (s.id * 17 % 100) / 50.0 - 1.0 +
        (s.id * 31 % 100) / 50.0 - 1.0 +
        (s.id * 53 % 100) / 50.0 - 1.0
    ) AS INT))),
    NOW() - ((10000 - s.id) * INTERVAL '2 minutes')
FROM generate_series(1, 10000) AS s(id);

-- 3. Generate 1,500 Game Sessions
INSERT INTO game_sessions (session_id, game_id, player_id, server_id, status, region, started_at, updated_at)
SELECT
    'ses-' || LPAD(s.id::text, 6, '0'),
    'match-' || LPAD(((s.id % 200) + 1)::text, 4, '0'),
    'ply-' || LPAD(s.id::text, 6, '0'),
    (ARRAY['srv-na-01', 'srv-na-02', 'srv-eu-01', 'srv-eu-02', 'srv-ap-01', 'srv-ap-02'])[(s.id % 6) + 1],
    CASE 
        WHEN s.id % 10 < 6 THEN 'active'
        WHEN s.id % 10 < 9 THEN 'completed'
        ELSE 'abandoned'
    END,
    (ARRAY['us-east', 'us-west', 'eu-central', 'eu-west', 'ap-southeast', 'ap-northeast'])[(s.id % 6) + 1],
    NOW() - ((1500 - s.id) * INTERVAL '15 seconds'),
    NOW() - ((1500 - s.id) * INTERVAL '5 seconds')
FROM generate_series(1, 1500) AS s(id);

-- 4. Generate 100,000 Game Events
INSERT INTO game_events (event_id, session_id, player_id, event_type, payload, event_time)
SELECT
    'evt-' || LPAD(s.id::text, 8, '0'),
    'ses-' || LPAD(((s.id % 1500) + 1)::text, 6, '0'),
    'ply-' || LPAD(((s.id % 10000) + 1)::text, 6, '0'),
    (ARRAY['player_position_sync', 'ability_cast', 'damage_taken', 'item_pickup', 'heartbeat'])[(s.id % 5) + 1],
    json_build_object(
        'seq', s.id,
        'tick', (s.id * 7) % 64,
        'pos_x', round(((s.id * 13) % 10000) / 10.0, 2),
        'pos_y', round(((s.id * 23) % 10000) / 10.0, 2),
        'pos_z', round(((s.id * 37) % 2000) / 10.0, 2)
    )::jsonb,
    NOW() - ((100000 - s.id) * INTERVAL '100 milliseconds')
FROM generate_series(1, 100000) AS s(id);

-- 5. Seed Catalog Index Metadata
INSERT INTO indexes (index_name, table_name, columns, status, captured_at)
VALUES
    ('idx_player_session', 'game_sessions', 'player_id, status', 'active', NOW()),
    ('idx_sessions_server_status', 'game_sessions', 'server_id, status', 'active', NOW()),
    ('idx_players_region_skill', 'players', 'region, skill_rating DESC', 'active', NOW()),
    ('idx_game_events_session_time', 'game_events', 'session_id, event_time DESC', 'active', NOW()),
    ('idx_query_exec_fp_time', 'query_executions', 'query_fingerprint, event_time DESC', 'active', NOW())
ON CONFLICT (index_name) DO UPDATE SET status = EXCLUDED.status, captured_at = EXCLUDED.captured_at;

-- 6. Seed Release History
INSERT INTO releases (release_id, version, deployed_at, description, schema_change, index_change)
VALUES
    ('rel-v2.2.0', 'v2.2.0', NOW() - INTERVAL '3 days', 'Multiplayer matchmaking optimization', FALSE, FALSE),
    ('rel-v2.3.0', 'v2.3.0', NOW() - INTERVAL '1 day', 'Region-based latency routing upgrade', FALSE, FALSE),
    ('rel-v2.3.1', 'v2.3.1', NOW() - INTERVAL '15 minutes', 'Session table partition & index restructuring', TRUE, TRUE)
ON CONFLICT (release_id) DO NOTHING;

-- 7. Seed Initial Statistics Snapshot
INSERT INTO statistics_snapshots (table_name, captured_at, row_count, dead_tuples, last_analyze, estimated_rows, actual_rows)
VALUES
    ('players', NOW() - INTERVAL '1 hour', 10000, 12, NOW() - INTERVAL '1 hour', 10000, 10000),
    ('game_sessions', NOW() - INTERVAL '1 hour', 1500, 85, NOW() - INTERVAL '1 hour', 1500, 1500),
    ('game_events', NOW() - INTERVAL '1 hour', 100000, 450, NOW() - INTERVAL '1 hour', 100000, 100000);
