"""
engine/feature_builder.py
-------------------------
Computes per-account graph and behavioural features from a transaction set.

The public surface is intentionally minimal:

    df = build_features(accounts_df, transactions_df)
    save_features(df, path)

Both functions work with pandas DataFrames so they compose naturally with
downstream analysis and the evaluate module.

Feature definitions
  in_degree       — unique senders to this account
  out_degree      — unique receivers from this account
  total_in        — cumulative USD received
  total_out       — cumulative USD sent
  velocity_score  — (in_degree + out_degree) / active_days
  imbalance_score — |total_out - total_in| / (total_out + total_in + 1)
"""

import pandas as pd


def build_features(
    accounts_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute all six features for every account.

    Parameters
    ----------
    accounts_df     : DataFrame with columns [account_id, account_type, is_mule]
    transactions_df : DataFrame with columns [from_account, to_account, amount, timestamp]

    Returns
    -------
    DataFrame indexed by account_id with all FEATURE_FIELDS columns.
    """
    tx = transactions_df[["from_account", "to_account", "amount", "timestamp"]].copy()
    tx["day"] = tx["timestamp"].str[:10]

    in_degree = (
        tx.groupby("to_account")["from_account"]
        .nunique()
        .rename("in_degree")
    )
    out_degree = (
        tx.groupby("from_account")["to_account"]
        .nunique()
        .rename("out_degree")
    )
    total_in = (
        tx.groupby("to_account")["amount"]
        .sum()
        .rename("total_in")
    )
    total_out = (
        tx.groupby("from_account")["amount"]
        .sum()
        .rename("total_out")
    )

    active_days_as_sender   = tx.groupby("from_account")["day"].nunique().rename("days_out")
    active_days_as_receiver = tx.groupby("to_account")["day"].nunique().rename("days_in")

    features = (
        accounts_df[["account_id", "account_type", "is_mule"]]
        .set_index("account_id")
        .join(in_degree,   how="left")
        .join(out_degree,  how="left")
        .join(total_in,    how="left")
        .join(total_out,   how="left")
        .join(active_days_as_sender,   how="left")
        .join(active_days_as_receiver, how="left")
        .fillna(0)
    )

    features["active_days"]    = (features["days_out"] + features["days_in"]).clip(lower=1)
    features["degree"]         = features["in_degree"] + features["out_degree"]
    features["velocity_score"] = (features["degree"] / features["active_days"]).round(4)

    denom = features["total_in"] + features["total_out"] + 1.0
    features["imbalance_score"] = (
        (features["total_out"] - features["total_in"]).abs() / denom
    ).round(4)

    features = features.drop(columns=["active_days", "degree", "days_out", "days_in"])
    features = features.astype({
        "in_degree":  int,
        "out_degree": int,
        "total_in":   float,
        "total_out":  float,
    })
    features[["total_in", "total_out"]] = features[["total_in", "total_out"]].round(2)

    return features.reset_index()


def save_features(features_df: pd.DataFrame, path: str) -> None:
    """Write the features DataFrame to a CSV file at the given path."""
    features_df.to_csv(path, index=False)
