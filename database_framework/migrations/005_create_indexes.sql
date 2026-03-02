-- ============================================================
-- INDEXES
-- Critical for query performance at 4M accounts / 20M transactions
-- ============================================================

-- Accounts indexes
CREATE INDEX IF NOT EXISTS idx_accounts_external_id
    ON accounts(external_id);

CREATE INDEX IF NOT EXISTS idx_accounts_flagged
    ON accounts(is_flagged)
    WHERE is_flagged = TRUE;

CREATE INDEX IF NOT EXISTS idx_accounts_risk_score
    ON accounts(risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_accounts_country
    ON accounts(country_code);

-- Transactions indexes
CREATE INDEX IF NOT EXISTS idx_tx_sender
    ON transactions(sender_id, initiated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tx_receiver
    ON transactions(receiver_id, initiated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tx_time
    ON transactions(initiated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tx_amount
    ON transactions(amount DESC);

CREATE INDEX IF NOT EXISTS idx_tx_external_id
    ON transactions(external_id);

-- Alerts indexes
CREATE INDEX IF NOT EXISTS idx_alerts_account
    ON alerts(account_id, fired_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_unresolved
    ON alerts(is_resolved, severity)
    WHERE is_resolved = FALSE;

CREATE INDEX IF NOT EXISTS idx_alerts_campaign
    ON alerts(campaign_id);

CREATE INDEX IF NOT EXISTS idx_alerts_fired_at
    ON alerts(fired_at DESC);

-- Snapshots indexes
CREATE INDEX IF NOT EXISTS idx_snapshots_captured_at
    ON graph_snapshots(captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_phase_shifts_detected_at
    ON phase_shift_events(detected_at DESC);