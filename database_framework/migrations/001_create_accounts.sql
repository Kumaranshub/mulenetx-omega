-- ============================================================
-- ACCOUNTS TABLE
-- 4 million rows expected
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    account_id      BIGSERIAL PRIMARY KEY,
    external_id     VARCHAR(64) UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    account_type    VARCHAR(32),
    country_code    CHAR(2),
    risk_score      FLOAT DEFAULT 0.0,
    flow_potential  FLOAT DEFAULT 0.0,
    is_flagged      BOOLEAN DEFAULT FALSE,
    flagged_at      TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

COMMENT ON TABLE accounts IS 'All financial accounts in the mule detection network';
COMMENT ON COLUMN accounts.risk_score IS 'Latest GNN fraud score (0.0 = clean, 1.0 = certain fraud)';
COMMENT ON COLUMN accounts.flow_potential IS 'Thermodynamic flow potential from Laplacian solver';
COMMENT ON COLUMN accounts.is_flagged IS 'True if account is flagged as mule by any detector';