-- ============================================================
-- GRAPH EDGE VIEW
-- Converts transactions into directed edges for GNN
-- ============================================================

CREATE OR REPLACE VIEW graph_edges AS
SELECT
    sender_id AS source,
    receiver_id AS target,
    amount,
    initiated_at
FROM transactions;

COMMENT ON VIEW graph_edges IS
'Directed edges derived from transactions for graph ML';


-- ============================================================
-- NODE FEATURE VIEW
-- Basic account features for the GNN
-- ============================================================

CREATE OR REPLACE VIEW account_features AS
SELECT
    a.account_id,

    COUNT(DISTINCT t_out.transaction_id) AS out_degree,
    COUNT(DISTINCT t_in.transaction_id) AS in_degree,

    COALESCE(SUM(t_out.amount),0) AS total_outflow,
    COALESCE(SUM(t_in.amount),0) AS total_inflow

FROM accounts a

LEFT JOIN transactions t_out
ON a.account_id = t_out.sender_id

LEFT JOIN transactions t_in
ON a.account_id = t_in.receiver_id

GROUP BY a.account_id;

COMMENT ON VIEW account_features IS
'Node features used by the GNN fraud model';
