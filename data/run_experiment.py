"""
data/run_experiment.py
----------------------
MuleNet-X Omega — Experiment Runner

Creates a fully isolated, reproducible run under data/runs/<run_id>/ and
produces the complete output artefact set:

    accounts.csv
    transactions.csv
    features.csv
    risk_scores.csv
    summary.json
    snapshots/day_1.csv … day_N.csv   (if --snapshot-days > 0)

Each run is identified by a timestamp-based run_id so experiments never
overwrite each other.

Usage examples
    python data/run_experiment.py
    python data/run_experiment.py --accounts 1000 --fraud-pattern star
    python data/run_experiment.py --fraud-pattern funnel --snapshot-days 7
    python data/run_experiment.py --stream --seed 99
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Make engine importable when called from the project root or from data/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from engine.models import SimConfig, ACCOUNT_FIELDS, TRANSACTION_FIELDS, FEATURE_FIELDS, RISK_FIELDS
from engine.rng import seed_all
from engine.accounts import generate_accounts, partition_by_type
from engine.transactions import generate_normal_transactions, generate_business_transactions
from engine.patterns import generate_fraud_transactions
from engine.feature_builder import build_features, save_features
from engine.risk_baseline import compute_risk_scores, save_risk_scores
from engine.io import (
    write_csv, stream_csv, write_summary_json, write_snapshots, print_run_summary,
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MuleNet-X Omega experiment runner.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--accounts",       type=int,   default=500,      metavar="N",
                   help="Total number of accounts.")
    p.add_argument("--transactions",   type=int,   default=3000,     metavar="N",
                   help="Approximate total transactions.")
    p.add_argument("--mule-ratio",     type=float, default=0.08,     metavar="F",
                   dest="mule_ratio",
                   help="Fraction of accounts that are mules (0–1).")
    p.add_argument("--fraud-pattern",  type=str,   default="linear",
                   choices=["linear", "star", "circular", "funnel"],
                   dest="fraud_pattern",
                   help="Fraud topology to simulate.")
    p.add_argument("--seed",           type=int,   default=42,       metavar="INT")
    p.add_argument("--snapshot-days",  type=int,   default=0,        metavar="N",
                   dest="snapshot_days",
                   help="Generate N daily cumulative snapshots (0 = disabled).")
    p.add_argument("--stream",         action="store_true", default=False,
                   help="Write transactions incrementally with progress logs.")
    p.add_argument("--base-dir",       type=str,   default="data/runs",
                   dest="base_dir",
                   help="Parent directory for experiment runs.")
    return p.parse_args()


def build_config(args: argparse.Namespace, out_dir: str) -> SimConfig:
    return SimConfig(
        total_accounts=args.accounts,
        mule_pct=args.mule_ratio,
        business_pct=0.10,
        total_transactions=args.transactions,
        seed=args.seed,
        out_dir=out_dir,
        stream=args.stream,
        fraud_pattern=args.fraud_pattern,
        snapshot_days=args.snapshot_days,
    )


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

def run_experiment(cfg: SimConfig, run_id: str) -> None:
    os.makedirs(cfg.out_dir, exist_ok=True)
    paths = {
        "config":       os.path.join(cfg.out_dir, "config.json"),
        "accounts":     os.path.join(cfg.out_dir, "accounts.csv"),
        "transactions": os.path.join(cfg.out_dir, "transactions.csv"),
        "features":     os.path.join(cfg.out_dir, "features.csv"),
        "risk_scores":  os.path.join(cfg.out_dir, "risk_scores.csv"),
        "summary":      os.path.join(cfg.out_dir, "summary.json"),
        "snapshots":    os.path.join(cfg.out_dir, "snapshots"),
    }

    # Persist config immediately so the run is reproducible even if it fails.
    with open(paths["config"], "w") as fh:
        import dataclasses
        json.dump(dataclasses.asdict(cfg), fh, indent=2, default=str)
    print(f"  → {paths['config']}")

    # -----------------------------------------------------------------------
    # 1. Accounts
    # -----------------------------------------------------------------------
    print(f"\n[1/6] Generating {cfg.total_accounts:,} accounts …")
    rng      = seed_all(cfg.seed)
    accounts = generate_accounts(cfg, rng)
    groups   = partition_by_type(accounts)
    all_ids  = [a.account_id for a in accounts]

    write_csv(paths["accounts"], ACCOUNT_FIELDS, [a.to_dict() for a in accounts])
    print(f"  → {paths['accounts']}")

    # -----------------------------------------------------------------------
    # 2 & 3. Legitimate transactions
    # -----------------------------------------------------------------------
    n_mule_chains = max(1, len(groups["mule"]) // 3)
    remaining     = max(0, cfg.total_transactions - n_mule_chains * 5)
    n_business_tx = int(remaining * 0.40)
    n_normal_tx   = remaining - n_business_tx

    print(f"[2/6] Generating ~{n_normal_tx:,} normal transactions …")
    normal_tx = generate_normal_transactions(groups["normal"], all_ids, n_normal_tx, rng)

    print(f"[3/6] Generating {n_business_tx:,} business transactions …")
    business_tx = generate_business_transactions(groups["business"], all_ids, n_business_tx, rng)

    # -----------------------------------------------------------------------
    # 4. Fraud pattern
    # -----------------------------------------------------------------------
    print(f"[4/6] Generating {n_mule_chains} '{cfg.fraud_pattern}' fraud chains …")
    mule_tx, chains_created = generate_fraud_transactions(
        pattern=cfg.fraud_pattern,
        mule_ids=groups["mule"],
        normal_ids=groups["normal"],
        n_chains=n_mule_chains,
        rng=rng,
    )

    all_tx = sorted(normal_tx + business_tx + mule_tx, key=lambda t: t.timestamp)
    tx_rows = [t.to_dict() for t in all_tx]

    if cfg.stream:
        print(f"[STREAM] → {paths['transactions']}")
        stream_csv(paths["transactions"], TRANSACTION_FIELDS, tx_rows,
                   batch_size=max(1, len(tx_rows) // 40))
    else:
        write_csv(paths["transactions"], TRANSACTION_FIELDS, tx_rows)
        print(f"  → {paths['transactions']}")

    # -----------------------------------------------------------------------
    # 5. Features
    # -----------------------------------------------------------------------
    print("[5/6] Computing features and risk scores …")
    accounts_df     = pd.DataFrame([a.to_dict() for a in accounts])
    transactions_df = pd.DataFrame(tx_rows)

    features_df = build_features(accounts_df, transactions_df)
    save_features(features_df, paths["features"])
    print(f"  → {paths['features']}")

    risk_df = compute_risk_scores(features_df)
    save_risk_scores(risk_df, paths["risk_scores"])
    print(f"  → {paths['risk_scores']}")

    # -----------------------------------------------------------------------
    # 6. Summary + snapshots
    # -----------------------------------------------------------------------
    print("[6/6] Writing summary and snapshots …")
    write_summary_json(paths["summary"], accounts, all_tx, chains_created, cfg, run_id)
    print(f"  → {paths['summary']}")

    if cfg.snapshot_days > 0:
        write_snapshots(paths["snapshots"], all_tx, cfg.snapshot_days)

    print_run_summary(accounts, all_tx, chains_created, run_id, cfg.out_dir)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args   = parse_args()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(args.base_dir, run_id)

    print(f"\n  MuleNet-X Omega  |  run_id: {run_id}")
    print(f"  pattern: {args.fraud_pattern}  |  seed: {args.seed}")
    print(f"  output:  {out_dir}\n")

    cfg = build_config(args, out_dir)
    run_experiment(cfg, run_id)


if __name__ == "__main__":
    main()
