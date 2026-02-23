"""
analysis/evaluate.py
--------------------
Evaluates the baseline risk scorer against ground-truth mule labels.

Loads features.csv and risk_scores.csv from a completed experiment run,
thresholds the risk score to produce binary predictions, computes standard
fraud-detection metrics, and saves them to metrics.json.

Usage
    python analysis/evaluate.py --run-dir data/runs/<run_id>
    python analysis/evaluate.py --run-dir data/runs/<run_id> --threshold 0.6
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
)


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

def load_run(run_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load features.csv and risk_scores.csv from a run directory."""
    features_path = os.path.join(run_dir, "features.csv")
    risk_path     = os.path.join(run_dir, "risk_scores.csv")

    missing = [p for p in [features_path, risk_path] if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    features = pd.read_csv(features_path)
    risk     = pd.read_csv(risk_path)
    return features, risk


def evaluate(
    features_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    threshold: float = 0.5,
) -> dict:
    """
    Merge labels with scores and compute binary classification metrics.

    Parameters
    ----------
    features_df : must contain [account_id, is_mule]
    risk_df     : must contain [account_id, risk_score]
    threshold   : risk_score ≥ threshold is classified as fraud

    Returns
    -------
    dict with keys: threshold, precision, recall, f1, roc_auc, support
    """
    merged = features_df[["account_id", "is_mule"]].merge(
        risk_df[["account_id", "risk_score"]], on="account_id", how="inner"
    )

    y_true = merged["is_mule"].astype(int)
    y_prob = merged["risk_score"].astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    n_mules   = int(y_true.sum())
    n_total   = len(y_true)
    n_flagged = int(y_pred.sum())

    metrics = {
        "threshold":     threshold,
        "total_accounts": n_total,
        "true_mules":     n_mules,
        "flagged":        n_flagged,
        "precision":      round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall":         round(float(recall_score(y_true, y_pred, zero_division=0)),    4),
        "f1":             round(float(f1_score(y_true, y_pred, zero_division=0)),        4),
        "roc_auc":        round(float(roc_auc_score(y_true, y_prob)), 4),
    }
    return metrics, y_true, y_pred


def print_results(metrics: dict, y_true, y_pred) -> None:
    """Pretty-print metrics to stdout."""
    w = 52
    print("\n" + "=" * w)
    print("   MuleNet-X Omega — Evaluation Results")
    print("=" * w)
    print(f"   Threshold       : {metrics['threshold']}")
    print(f"   Total accounts  : {metrics['total_accounts']:>7,}")
    print(f"   True mules      : {metrics['true_mules']:>7,}")
    print(f"   Flagged by model: {metrics['flagged']:>7,}")
    print(f"\n   Precision       : {metrics['precision']:.4f}")
    print(f"   Recall          : {metrics['recall']:.4f}")
    print(f"   F1 Score        : {metrics['f1']:.4f}")
    print(f"   ROC AUC         : {metrics['roc_auc']:.4f}")
    print("\n" + "-" * w)
    print(classification_report(y_true, y_pred, target_names=["normal", "mule"],
                                 zero_division=0))
    print("=" * w + "\n")


def save_metrics(metrics: dict, run_dir: str) -> None:
    """Write metrics dict to metrics.json inside the run directory."""
    path = os.path.join(run_dir, "metrics.json")
    with open(path, "w") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"  → {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Evaluate MuleNet-X Omega baseline risk scorer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--run-dir", dest="run_dir", required=True, metavar="DIR",
        help="Path to a completed experiment run directory.",
    )
    p.add_argument(
        "--threshold", type=float, default=0.5, metavar="F",
        help="Risk score threshold for binary fraud classification.",
    )
    return p.parse_args()


def main() -> None:
    args     = parse_args()
    features, risk = load_run(args.run_dir)
    metrics, y_true, y_pred = evaluate(features, risk, threshold=args.threshold)
    print_results(metrics, y_true, y_pred)
    save_metrics(metrics, args.run_dir)


if __name__ == "__main__":
    main()
