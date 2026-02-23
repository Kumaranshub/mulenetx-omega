import csv
import json
import os
import time
import uuid
import random
import argparse
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

try:
    import numpy as _np
    _np.random.seed  # verify it's usable
    _NUMPY = True
except Exception:
    _NUMPY = False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SimConfig:
    total_accounts:     int   = 500
    mule_pct:           float = 0.08
    business_pct:       float = 0.10
    total_transactions: int   = 3000
    seed:               int   = 42
    out_dir:            str   = "."
    stream:             bool  = False


@dataclass(frozen=True)
class SimWindow:
    start: datetime = datetime(2024, 1, 1)
    days:  int      = 180

    @property
    def end(self) -> datetime:
        return self.start + timedelta(days=self.days)


WINDOW = SimWindow()

CHANNELS        = ["mobile", "web", "atm"]
CHANNEL_WEIGHTS = [0.55, 0.35, 0.10]
REGIONS         = ["US-WEST", "US-EAST", "EU-WEST", "EU-EAST", "APAC", "LATAM"]

BURST_PROBABILITY  = 0.05
BURST_CLUSTER_SIZE = (3, 8)

ACCOUNT_FIELDS     = ["account_id", "created_at", "account_type", "is_mule"]
TRANSACTION_FIELDS = ["from_account", "to_account", "amount", "timestamp",
                      "label", "device_id", "channel", "region"]
FEATURE_FIELDS     = ["account_id", "account_type", "is_mule",
                      "in_degree", "out_degree", "total_in", "total_out",
                      "velocity_score", "imbalance_score"]


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

@dataclass
class Account:
    account_id:   str
    created_at:   str
    account_type: str
    is_mule:      bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Transaction:
    from_account: str
    to_account:   str
    amount:       float
    timestamp:    str
    label:        str
    device_id:    str
    channel:      str
    region:       str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AccountFeatures:
    account_id:      str
    account_type:    str
    is_mule:         bool
    in_degree:       int
    out_degree:      int
    total_in:        float
    total_out:       float
    velocity_score:  float
    imbalance_score: float

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# RNG primitives
# ---------------------------------------------------------------------------

def seed_all(seed: int) -> random.Random:
    random.seed(seed)
    if _NUMPY:
        _np.random.seed(seed)
    return random.Random(seed)


def random_datetime(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(0, span)))


def lognormal_amount(rng: random.Random, mu: float, sigma: float,
                     lo: float, hi: float) -> float:
    return round(max(lo, min(rng.lognormvariate(mu, sigma), hi)), 2)


def pick_channel(rng: random.Random,
                 channels: list[str] = CHANNELS,
                 weights: list[float] = CHANNEL_WEIGHTS) -> str:
    return rng.choices(channels, weights=weights, k=1)[0]


def new_device_id(rng: random.Random) -> str:
    return "DEV-" + format(rng.getrandbits(48), "012x").upper()


def make_transaction(rng: random.Random, sender: str, receiver: str,
                     amount: float, ts: datetime, label: str,
                     channel_override: Optional[str] = None) -> Transaction:
    return Transaction(
        from_account=sender,
        to_account=receiver,
        amount=amount,
        timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
        label=label,
        device_id=new_device_id(rng),
        channel=channel_override or pick_channel(rng),
        region=rng.choice(REGIONS),
    )


# ---------------------------------------------------------------------------
# Account generation
# ---------------------------------------------------------------------------

def generate_accounts(cfg: SimConfig, rng: random.Random) -> list[Account]:
    n_mules    = max(2, int(cfg.total_accounts * cfg.mule_pct))
    n_business = max(2, int(cfg.total_accounts * cfg.business_pct))
    n_normal   = cfg.total_accounts - n_mules - n_business

    def build(account_type: str) -> Account:
        created_at = WINDOW.start + timedelta(days=rng.randint(0, WINDOW.days - 1))
        return Account(
            account_id=str(uuid.UUID(int=rng.getrandbits(128))),
            created_at=created_at.strftime("%Y-%m-%d"),
            account_type=account_type,
            is_mule=account_type == "mule",
        )

    accounts = (
        [build("normal")   for _ in range(n_normal)]
        + [build("business") for _ in range(n_business)]
        + [build("mule")     for _ in range(n_mules)]
    )
    rng.shuffle(accounts)
    return accounts


def partition_by_type(accounts: list[Account]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"normal": [], "business": [], "mule": []}
    for acc in accounts:
        groups[acc.account_type].append(acc.account_id)
    return groups


# ---------------------------------------------------------------------------
# Transaction generators
# ---------------------------------------------------------------------------

def generate_normal_transactions(normal_ids: list[str], all_ids: list[str],
                                  target: int, rng: random.Random) -> list[Transaction]:
    if not normal_ids or target == 0:
        return []

    tx: list[Transaction] = []
    i = 0

    while i < target:
        sender    = rng.choice(normal_ids)
        receiver  = rng.choice([a for a in all_ids if a != sender])
        hour      = int(rng.triangular(6, 23, 19))
        ts        = WINDOW.start + timedelta(
            days=rng.randint(0, WINDOW.days - 1),
            hours=hour,
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )
        amount    = lognormal_amount(rng, mu=4.5, sigma=1.2, lo=1.0, hi=5_000.0)
        tx.append(make_transaction(rng, sender, receiver, amount,
                                   min(ts, WINDOW.end), "normal"))
        i += 1

        if rng.random() < BURST_PROBABILITY and i < target:
            burst_count = rng.randint(*BURST_CLUSTER_SIZE)
            for _ in range(min(burst_count, target - i)):
                burst_rx  = rng.choice([a for a in all_ids if a != sender])
                burst_ts  = min(ts + timedelta(seconds=rng.randint(30, 1_800)), WINDOW.end)
                burst_amt = lognormal_amount(rng, mu=4.2, sigma=0.9, lo=1.0, hi=2_000.0)
                tx.append(make_transaction(rng, sender, burst_rx, burst_amt,
                                           burst_ts, "normal"))
                i += 1

    return tx


def generate_business_transactions(business_ids: list[str], all_ids: list[str],
                                    target: int, rng: random.Random) -> list[Transaction]:
    if not business_ids or target == 0:
        return []

    tx: list[Transaction] = []
    for _ in range(target):
        sender   = rng.choice(business_ids)
        receiver = rng.choice([a for a in all_ids if a != sender])
        ts = WINDOW.start + timedelta(
            days=rng.randint(0, WINDOW.days - 1),
            hours=int(rng.triangular(8, 18, 13)),
            minutes=rng.randint(0, 59),
        )
        amount  = lognormal_amount(rng, mu=6.2, sigma=0.9, lo=10.0, hi=10_000.0)
        channel = pick_channel(rng, channels=["web", "mobile", "atm"],
                               weights=[0.70, 0.28, 0.02])
        tx.append(make_transaction(rng, sender, receiver, amount,
                                   min(ts, WINDOW.end), "normal",
                                   channel_override=channel))
    return tx


def generate_mule_chains(mule_ids: list[str], normal_ids: list[str],
                          n_chains: int, rng: random.Random) -> tuple[list[Transaction], int]:
    if len(mule_ids) < 2 or n_chains == 0:
        return [], 0

    n_hubs     = max(1, len(mule_ids) // 5)
    hub_pool   = mule_ids[:n_hubs]
    leaf_pool  = mule_ids[n_hubs:]
    tx:   list[Transaction] = []
    built = 0

    for _ in range(n_chains):
        chain_len   = rng.randint(3, 7)
        max_start_s = max(1, WINDOW.days * 86_400 - 7_200)
        chain_start = WINDOW.start + timedelta(seconds=rng.randint(0, max_start_s))

        use_hub = len(leaf_pool) >= 2 and rng.random() < 0.6
        if use_hub:
            hub   = rng.choice(hub_pool)
            pool  = leaf_pool if len(leaf_pool) >= chain_len - 1 else mule_ids
            nodes = (rng.sample(pool, min(chain_len - 1, len(pool)))
                     if len(pool) >= chain_len - 1
                     else rng.choices(pool, k=chain_len - 1))
            nodes.insert(len(nodes) // 2, hub)
        else:
            nodes = (rng.sample(mule_ids, chain_len)
                     if len(mule_ids) >= chain_len
                     else rng.choices(mule_ids, k=chain_len))

        entry_sender = rng.choice(normal_ids) if normal_ids else nodes[-1]
        entry_amount = round(rng.uniform(5_000, 50_000), 2)
        mule_channel = rng.choice(["mobile", "web"])
        current_ts   = chain_start
        current_amt  = entry_amount

        tx.append(make_transaction(rng, entry_sender, nodes[0], current_amt,
                                   current_ts, "mule_flow",
                                   channel_override=mule_channel))

        for i in range(len(nodes) - 1):
            current_ts  = current_ts + timedelta(seconds=rng.randint(30, 900))
            current_amt = max(1.0, round(
                current_amt * (1 - rng.uniform(0.01, 0.03))
                + rng.uniform(-0.50, 0.50), 2
            ))
            tx.append(make_transaction(rng, nodes[i], nodes[i + 1], current_amt,
                                       current_ts, "mule_flow",
                                       channel_override=rng.choice(["mobile", "web"])))
        built += 1

    return tx, built


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def generate_features(accounts: list[Account],
                       transactions: list[Transaction]) -> list[AccountFeatures]:
    in_senders:    dict[str, set[str]] = defaultdict(set)
    out_receivers: dict[str, set[str]] = defaultdict(set)
    total_in:      dict[str, float]    = defaultdict(float)
    total_out:     dict[str, float]    = defaultdict(float)
    active_days:   dict[str, set[str]] = defaultdict(set)

    for tx in transactions:
        out_receivers[tx.from_account].add(tx.to_account)
        in_senders[tx.to_account].add(tx.from_account)
        total_out[tx.from_account] += tx.amount
        total_in[tx.to_account]    += tx.amount
        day = tx.timestamp[:10]
        active_days[tx.from_account].add(day)
        active_days[tx.to_account].add(day)

    features = []
    for acc in accounts:
        aid     = acc.account_id
        t_in    = round(total_in[aid], 2)
        t_out   = round(total_out[aid], 2)
        n_days  = max(1, len(active_days[aid]))
        degree  = len(in_senders[aid]) + len(out_receivers[aid])
        denom   = t_in + t_out + 1.0

        features.append(AccountFeatures(
            account_id=aid,
            account_type=acc.account_type,
            is_mule=acc.is_mule,
            in_degree=len(in_senders[aid]),
            out_degree=len(out_receivers[aid]),
            total_in=t_in,
            total_out=t_out,
            velocity_score=round(degree / n_days, 4),
            imbalance_score=round(abs(t_out - t_in) / denom, 4),
        ))
    return features


# ---------------------------------------------------------------------------
# I/O layer
# ---------------------------------------------------------------------------

def write_csv(path: str, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stream_csv(path: str, fieldnames: list[str], rows: list[dict],
               batch_size: int, delay_s: float) -> None:
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


def write_summary(path: str, accounts: list[Account],
                  transactions: list[Transaction],
                  n_chains: int, cfg: SimConfig) -> None:
    groups = partition_by_type(accounts)
    label_counts: dict[str, int] = defaultdict(int)
    timestamps = []
    for tx in transactions:
        label_counts[tx.label] += 1
        timestamps.append(tx.timestamp)
    timestamps.sort()

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_params": {
            "total_accounts":     len(accounts),
            "mule_pct":           cfg.mule_pct,
            "business_pct":       cfg.business_pct,
            "total_transactions": len(transactions),
            "random_seed":        cfg.seed,
            "out_dir":            cfg.out_dir,
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


def print_run_summary(accounts: list[Account], transactions: list[Transaction],
                      n_chains: int, out_dir: str) -> None:
    groups = partition_by_type(accounts)
    total  = len(accounts)
    label_counts: dict[str, int] = defaultdict(int)
    for tx in transactions:
        label_counts[tx.label] += 1

    w = 54
    print("\n" + "=" * w)
    print("   Fraud Data Generator — Run Summary")
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Synthetic financial transaction generator for fraud detection.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--accounts",      type=int,   default=SimConfig.total_accounts,     metavar="N")
    p.add_argument("--mule-pct",      type=float, default=SimConfig.mule_pct,           metavar="F", dest="mule_pct")
    p.add_argument("--business-pct",  type=float, default=SimConfig.business_pct,       metavar="F", dest="business_pct")
    p.add_argument("--transactions",  type=int,   default=SimConfig.total_transactions, metavar="N")
    p.add_argument("--seed",          type=int,   default=SimConfig.seed,               metavar="INT")
    p.add_argument("--out-dir",       type=str,   default=SimConfig.out_dir,            metavar="DIR", dest="out_dir")
    p.add_argument("--stream",        action="store_true", default=False)
    p.add_argument("--accounts-file",     default=None, help=argparse.SUPPRESS, dest="_accounts_file")
    p.add_argument("--transactions-file", default=None, help=argparse.SUPPRESS, dest="_transactions_file")
    return p.parse_args()


def build_config(args: argparse.Namespace) -> SimConfig:
    return SimConfig(
        total_accounts=args.accounts,
        mule_pct=args.mule_pct,
        business_pct=args.business_pct,
        total_transactions=args.transactions,
        seed=args.seed,
        out_dir=args.out_dir,
        stream=args.stream,
    )


def resolve_paths(cfg: SimConfig, args: argparse.Namespace) -> dict[str, str]:
    d = cfg.out_dir
    return {
        "accounts":     args._accounts_file     or os.path.join(d, "accounts.csv"),
        "transactions": args._transactions_file or os.path.join(d, "transactions.csv"),
        "features":     os.path.join(d, "features.csv"),
        "summary":      os.path.join(d, "summary.json"),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(cfg: SimConfig, paths: dict[str, str]) -> None:
    rng = seed_all(cfg.seed)
    os.makedirs(cfg.out_dir, exist_ok=True)

    print(f"[1/6] Generating {cfg.total_accounts:,} accounts …")
    accounts = generate_accounts(cfg, rng)
    groups   = partition_by_type(accounts)
    all_ids  = [a.account_id for a in accounts]

    n_mule_chains = max(1, len(groups["mule"]) // 3)
    remaining     = max(0, cfg.total_transactions - n_mule_chains * 5)
    n_business_tx = int(remaining * 0.40)
    n_normal_tx   = remaining - n_business_tx

    print(f"[2/6] Generating ~{n_normal_tx:,} normal transactions …")
    normal_tx = generate_normal_transactions(groups["normal"], all_ids, n_normal_tx, rng)

    print(f"[3/6] Generating {n_business_tx:,} business transactions …")
    business_tx = generate_business_transactions(groups["business"], all_ids, n_business_tx, rng)

    print(f"[4/6] Generating {n_mule_chains} mule chains …")
    mule_tx, chains_created = generate_mule_chains(groups["mule"], groups["normal"],
                                                    n_mule_chains, rng)

    all_tx = sorted(normal_tx + business_tx + mule_tx, key=lambda t: t.timestamp)

    print("[5/6] Extracting account features …")
    features = generate_features(accounts, all_tx)

    print("[6/6] Writing output files …")

    write_csv(paths["accounts"], ACCOUNT_FIELDS,
              [a.to_dict() for a in accounts])
    print(f"  → {paths['accounts']}")

    tx_rows = [t.to_dict() for t in all_tx]
    if cfg.stream:
        print(f"\n  [STREAM] → {paths['transactions']}")
        stream_csv(paths["transactions"], TRANSACTION_FIELDS, tx_rows,
                   batch_size=max(1, len(tx_rows) // 40), delay_s=0.05)
    else:
        write_csv(paths["transactions"], TRANSACTION_FIELDS, tx_rows)
        print(f"  → {paths['transactions']}")

    write_csv(paths["features"], FEATURE_FIELDS,
              [f.to_dict() for f in features])
    print(f"  → {paths['features']}")

    write_summary(paths["summary"], accounts, all_tx, chains_created, cfg)
    print(f"  → {paths['summary']}")

    print_run_summary(accounts, all_tx, chains_created, cfg.out_dir)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args  = parse_args()
    cfg   = build_config(args)
    paths = resolve_paths(cfg, args)
    run(cfg, paths)


if __name__ == "__main__":
    main()
