-- ============================================================
-- ALERTS TABLE
-- Output sink from the Go alert service
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts (
    alert_id        BIGSERIAL PRIMARY KEY,
    alert_type      VARCHAR(64) NOT NULL,
    severity        VARCHAR(16) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    account_id      BIGINT REFERENCES accounts(account_id),
    campaign_id     UUID,
    fired_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    is_resolved     BOOLEAN DEFAULT FALSE,
    score           FLOAT,
    explanation     JSONB,
    raw_payload     JSONB
);

COMMENT ON TABLE alerts IS 'All fraud alerts fired by any detector in the pipeline';
COMMENT ON COLUMN alerts.explanation IS 'GNN attention weights and top neighbor accounts that drove the score';
COMMENT ON COLUMN alerts.campaign_id IS 'Groups related alerts into a single fraud campaign';