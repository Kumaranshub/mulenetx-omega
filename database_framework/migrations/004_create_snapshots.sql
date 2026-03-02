-- ============================================================
-- GRAPH SNAPSHOTS TABLE
-- Periodic state dumps from the Julia engine
-- ============================================================

CREATE TABLE IF NOT EXISTS graph_snapshots (
    snapshot_id     BIGSERIAL PRIMARY KEY,
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_count      INTEGER,
    edge_count      INTEGER,
    modularity      FLOAT,
    flow_entropy    FLOAT,
    spectral_gap    FLOAT,
    snapshot_path   TEXT,
    metadata        JSONB
);

COMMENT ON TABLE graph_snapshots IS 'Periodic macro-state snapshots from the Julia phase detector';

-- ============================================================
-- PHASE SHIFT EVENTS TABLE
-- Campaign-level early warnings from PELT detector
-- ============================================================

CREATE TABLE IF NOT EXISTS phase_shift_events (
    event_id        BIGSERIAL PRIMARY KEY,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metric_name     VARCHAR(64),
    value_before    FLOAT,
    value_after     FLOAT,
    confidence      FLOAT,
    linked_alerts   BIGINT[],
    notes           TEXT
);

COMMENT ON TABLE phase_shift_events IS 'Network macro-state change points detected by PELT algorithm';