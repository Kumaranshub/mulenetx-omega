"""
engine/risk_baseline.py
-----------------------
Baseline fraud risk scorer for MuleNet-X Omega.

Computes a normalised composite risk score per account using three signals:

    risk = 0.4 * velocity_score_norm
         + 0.3 * imbalance_score          (already in [0, 1])
         + 0.3 * degree_score_norm

All component scores are min-max normalised to [0, 1] before weighting so
the final risk score is comparable across datasets of different sizes.

Output
------
risk_scores.csv  with columns [account_id, risk_score]
"""

import pandas as pd


def _minmax_norm(series: pd.Series) -> pd.Series:
    """Min-max normalise a series to [0, 1]. Returns 0.0 if range is zero."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.0, index=series.index)
    return (series - lo) / (hi - lo)


def compute_risk_scores(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a composite risk score for each account.

    Parameters
    ----------
    features_df : DataFrame produced by engine.feature_builder.build_features

    Returns
    -------
    DataFrame with columns [account_id, risk_score], risk_score in [0, 1].
    The is_mule ground-truth label is included for convenience but is NOT
    used in the score computation.
    """
    df = features_df.copy()

    degree = df["in_degree"] + df["out_degree"]

    velocity_norm  = _minmax_norm(df["velocity_score"])
    imbalance_norm = df["imbalance_score"]           # already normalised
    degree_norm    = _minmax_norm(degree)

    df["risk_score"] = (
        0.4 * velocity_norm
        + 0.3 * imbalance_norm
        + 0.3 * degree_norm
    ).round(4)

    return df[["account_id", "risk_score"]]


def save_risk_scores(risk_df: pd.DataFrame, path: str) -> None:
    """Write the risk scores DataFrame to a CSV file at the given path."""
    risk_df.to_csv(path, index=False)
