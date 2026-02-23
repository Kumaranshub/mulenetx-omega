"""
engine/io.py
------------
All file I/O for the MuleNet-X Omega pipeline.

Provides:
  write_csv          — write list-of-dicts to CSV
  stream_csv         — incremental CSV write with progress logs
  write_summary_json — serialise run metadata to summary.json
  write_snapshots    — generate daily cumulative transaction snapshot CSVs
  print_run_summary  — formatted console output
"""

import csv
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

from engine.models import (
    Account, Transaction, SimConfig,
    TRANSACTION_FIELDS,
)
from engine.accounts import partition_by_type


def write_csv(path: str, fieldnames: list[str], rows: list[dict]) -> None:
    """Write a list of dicts to a CSV file with a header row."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stream_csv(
    path: str,
    fieldnames: list[str],
    rows: list[dict],
    batch_size: int,
    delay_s: float = 0.05,
) -> None:
    """
    Write rows to CSV in incremental batches, printing timestamped progress.
    Simulates a live event-emission pipeline for demos and integration tests.
    """
    total   = len(rows)
    emitted = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        while emitted < total:
            batch    = rows[emitted : emitted + batch_size]
            writer.writerows(batch)
            fh.flush()
            emitted += len(batch)
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"  [{ts}] ▶  {emitted:>6,} / {total:,}  "
                  f"({100 * emitted / total:5.1f}%)")
            if emitted < total:
                time.sleep(delay_s)


def write_summary_json(
    path: str,
    accounts: list[Account],
    transactions: list[Transaction],
    n_chains: int,
    cfg: SimConfig,
    run_id: str,
) -> None:
    """Serialise a machine-readable run summary."""
    groups = partition_by_type(accounts)
    label_counts: dict[str, int] = defaultdict(int)
    timestamps = []
    for tx in transactions:
        label_counts[tx.label] += 1
        timestamps.append(tx.timestamp)
    timestamps.sort()

    payload = {
        "run_id":       run_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_params": {
            "total_accounts":     len(accounts),
            "mule_pct":           cfg.mule_pct,
            "business_pct":       cfg.business_pct,
            "total_transactions": len(transactions),
            "random_seed":        cfg.seed,
            "fraud_pattern":      cfg.fraud_pattern,
            "snapshot_days":      cfg.snapshot_days,
            "stream_mode":        cfg.stream,
        },
        "account_counts": {
            "total":    len(accounts),
            "normal":   len(groups["normal"]),
            "business": len(groups["business"]),
            "mule":     len(groups["mule"]),
        },
        "transaction_counts": {
            "total":     len(transactions),
            "normal":    label_counts["normal"],
            "mule_flow": label_counts["mule_flow"],
        },
        "mule_chains_created": n_chains,
        "timestamp_range": {
            "min": timestamps[0]  if timestamps else None,
            "max": timestamps[-1] if timestamps else None,
        },
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def write_snapshots(
    snapshot_dir: str,
    transactions: list[Transaction],
    snapshot_days: int,
) -> None:
    """
    Write daily cumulative transaction snapshot CSVs.

    Snapshot day N contains all transactions with timestamp ≤ day N.
    Files are written to snapshot_dir/day_1.csv … day_<snapshot_days>.csv.
    """
    if snapshot_days <= 0:
        return

    os.makedirs(snapshot_dir, exist_ok=True)
    from engine.models import WINDOW

    tx_rows = sorted([t.to_dict() for t in transactions], key=lambda r: r["timestamp"])

    for day_n in range(1, snapshot_days + 1):
        cutoff   = (WINDOW.start + timedelta(days=day_n)).strftime("%Y-%m-%d %H:%M:%S")
        snapshot = [r for r in tx_rows if r["timestamp"] <= cutoff]
        path     = os.path.join(snapshot_dir, f"day_{day_n}.csv")
        write_csv(path, TRANSACTION_FIELDS, snapshot)

    print(f"  → {snapshot_days} daily snapshots written to {snapshot_dir}/")


def print_run_summary(
    accounts: list[Account],
    transactions: list[Transaction],
    n_chains: int,
    run_id: str,
    out_dir: str,
) -> None:
    """Print a formatted run summary to stdout."""
    groups = partition_by_type(accounts)
    total  = len(accounts)
    label_counts: dict[str, int] = defaultdict(int)
    for tx in transactions:
        label_counts[tx.label] += 1

    w = 58
    print("\n" + "=" * w)
    print(f"   MuleNet-X Omega — Run {run_id}")
    print("=" * w)
    print(f"   Accounts          : {total:>7,}")
    print(f"     normal          : {len(groups['normal']):>7,}  "
          f"({100 * len(groups['normal']) / total:.1f}%)")
    print(f"     business        : {len(groups['business']):>7,}  "
          f"({100 * len(groups['business']) / total:.1f}%)")
    print(f"     mule            : {len(groups['mule']):>7,}  "
          f"({100 * len(groups['mule']) / total:.1f}%)")
    print(f"\n   Transactions      : {len(transactions):>7,}")
    print(f"     label=normal    : {label_counts['normal']:>7,}")
    print(f"     label=mule_flow : {label_counts['mule_flow']:>7,}")
    print(f"\n   Mule chains       : {n_chains:>7,}")
    print(f"   Output dir        : {os.path.abspath(out_dir)}")
    print("=" * w + "\n")
