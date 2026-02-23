"""
engine/patterns.py
------------------
Fraud pattern generators for MuleNet-X Omega.

Each pattern models a distinct money-laundering topology:

  linear   — A → B → C → D (sequential layering chain)
  star     — hub receives large entry, redistributes to many leaf mules
  circular — A → B → C → A (loop; funds cycle to obscure trail)
  funnel   — many normal accounts → aggregator → many exit accounts

All patterns label their transactions "mule_flow" and restrict channels to
mobile/web (no ATM during active laundering phases).

The public API is a single dispatcher:

    generate_fraud_transactions(pattern, mule_ids, normal_ids, n_chains, rng)
"""

import random
from datetime import timedelta
from typing import Callable

from engine.models import Transaction, WINDOW
from engine.rng import lognormal_amount, make_transaction


MuleChannels = ["mobile", "web"]


def _mule_channel(rng: random.Random) -> str:
    return rng.choice(MuleChannels)


def _chain_start(rng: random.Random) -> "datetime":
    from datetime import datetime
    max_offset = max(1, WINDOW.days * 86_400 - 7_200)
    return WINDOW.start + timedelta(seconds=rng.randint(0, max_offset))


def _safe_sample(pool: list[str], k: int, rng: random.Random) -> list[str]:
    if len(pool) >= k:
        return rng.sample(pool, k)
    return rng.choices(pool, k=k)


# ---------------------------------------------------------------------------
# Linear pattern  (A → B → C → D)
# ---------------------------------------------------------------------------

def _linear_chain(
    mule_ids: list[str],
    normal_ids: list[str],
    rng: random.Random,
) -> list[Transaction]:
    """
    Classic layering chain. Entry funds flow through 3–7 mule nodes in sequence.
    Each hop skims 1–3 % with small jitter, keeping amounts near-identical.
    """
    if len(mule_ids) < 2:
        return []

    n_hubs    = max(1, len(mule_ids) // 5)
    hub_pool  = mule_ids[:n_hubs]
    leaf_pool = mule_ids[n_hubs:]

    chain_len = rng.randint(3, 7)
    use_hub   = len(leaf_pool) >= 2 and rng.random() < 0.6

    if use_hub:
        hub   = rng.choice(hub_pool)
        nodes = _safe_sample(leaf_pool if len(leaf_pool) >= chain_len - 1 else mule_ids,
                             chain_len - 1, rng)
        nodes.insert(len(nodes) // 2, hub)
    else:
        nodes = _safe_sample(mule_ids, chain_len, rng)

    entry_sender = rng.choice(normal_ids) if normal_ids else nodes[-1]
    current_amt  = round(rng.uniform(5_000, 50_000), 2)
    current_ts   = _chain_start(rng)
    tx: list[Transaction] = []

    tx.append(make_transaction(rng, entry_sender, nodes[0], current_amt,
                               current_ts, "mule_flow",
                               channel_override=_mule_channel(rng)))

    for i in range(len(nodes) - 1):
        current_ts  = current_ts + timedelta(seconds=rng.randint(30, 900))
        current_amt = max(1.0, round(
            current_amt * (1 - rng.uniform(0.01, 0.03)) + rng.uniform(-0.50, 0.50), 2
        ))
        tx.append(make_transaction(rng, nodes[i], nodes[i + 1], current_amt,
                                   current_ts, "mule_flow",
                                   channel_override=_mule_channel(rng)))
    return tx


# ---------------------------------------------------------------------------
# Star pattern  (hub ← entry → leaf₁, leaf₂, … leafₙ)
# ---------------------------------------------------------------------------

def _star_chain(
    mule_ids: list[str],
    normal_ids: list[str],
    rng: random.Random,
) -> list[Transaction]:
    """
    A hub mule receives a large sum from a normal entry account then rapidly
    fans out to 4–8 leaf mules in near-simultaneous transfers.
    This mimics smurfing / structuring behaviour.
    """
    if len(mule_ids) < 3:
        return []

    hub         = rng.choice(mule_ids)
    leaf_pool   = [m for m in mule_ids if m != hub]
    n_leaves    = min(rng.randint(4, 8), len(leaf_pool))
    leaves      = _safe_sample(leaf_pool, n_leaves, rng)

    entry_sender = rng.choice(normal_ids) if normal_ids else leaves[0]
    entry_amt    = round(rng.uniform(10_000, 80_000), 2)
    entry_ts     = _chain_start(rng)
    tx: list[Transaction] = []

    tx.append(make_transaction(rng, entry_sender, hub, entry_amt,
                               entry_ts, "mule_flow",
                               channel_override=_mule_channel(rng)))

    share     = round(entry_amt / n_leaves, 2)
    current_ts = entry_ts
    for leaf in leaves:
        gap        = rng.randint(60, 600)
        current_ts = current_ts + timedelta(seconds=gap)
        jitter     = round(rng.uniform(-50.0, 50.0), 2)
        leaf_amt   = max(1.0, share + jitter)
        tx.append(make_transaction(rng, hub, leaf, leaf_amt,
                                   current_ts, "mule_flow",
                                   channel_override=_mule_channel(rng)))
    return tx


# ---------------------------------------------------------------------------
# Circular pattern  (A → B → C → A)
# ---------------------------------------------------------------------------

def _circular_chain(
    mule_ids: list[str],
    normal_ids: list[str],
    rng: random.Random,
) -> list[Transaction]:
    """
    Funds cycle through 3–6 mule nodes and return to the originator.
    The loop pattern deliberately obscures the money trail.
    A normal account seeds the cycle; the final hop exits to another normal account.
    """
    if len(mule_ids) < 3:
        return []

    loop_len  = min(rng.randint(3, 6), len(mule_ids))
    nodes     = _safe_sample(mule_ids, loop_len, rng)
    loop      = nodes + [nodes[0]]       # close the ring

    entry_sender = rng.choice(normal_ids) if normal_ids else nodes[0]
    exit_receiver = rng.choice(normal_ids) if normal_ids else nodes[-1]

    seed_amt   = round(rng.uniform(5_000, 40_000), 2)
    current_ts = _chain_start(rng)
    tx: list[Transaction] = []

    tx.append(make_transaction(rng, entry_sender, nodes[0], seed_amt,
                               current_ts, "mule_flow",
                               channel_override=_mule_channel(rng)))

    current_amt = seed_amt
    for i in range(len(loop) - 1):
        current_ts  = current_ts + timedelta(seconds=rng.randint(120, 1_200))
        current_amt = max(1.0, round(
            current_amt * (1 - rng.uniform(0.005, 0.02)) + rng.uniform(-1.0, 1.0), 2
        ))
        tx.append(make_transaction(rng, loop[i], loop[i + 1], current_amt,
                                   current_ts, "mule_flow",
                                   channel_override=_mule_channel(rng)))

    current_ts = current_ts + timedelta(seconds=rng.randint(300, 3_600))
    tx.append(make_transaction(rng, nodes[-1], exit_receiver, current_amt,
                               current_ts, "mule_flow",
                               channel_override=_mule_channel(rng)))
    return tx


# ---------------------------------------------------------------------------
# Funnel pattern  (many normals → aggregator → many exits)
# ---------------------------------------------------------------------------

def _funnel_chain(
    mule_ids: list[str],
    normal_ids: list[str],
    rng: random.Random,
) -> list[Transaction]:
    """
    Multiple normal accounts make small deposits into a single aggregator mule.
    After accumulation, the aggregator disperses funds to several exit accounts.
    This models layering via micropayments aggregation.
    """
    if len(mule_ids) < 2 or len(normal_ids) < 2:
        return []

    aggregator  = rng.choice(mule_ids)
    exit_pool   = [m for m in mule_ids if m != aggregator]
    n_inputs    = min(rng.randint(4, 10), len(normal_ids))
    n_exits     = min(rng.randint(2, 5),  max(1, len(exit_pool)))
    feeders     = _safe_sample(normal_ids, n_inputs, rng)
    exits       = _safe_sample(exit_pool,  n_exits,  rng)

    accumulation_start = _chain_start(rng)
    current_ts         = accumulation_start
    total_collected    = 0.0
    tx: list[Transaction] = []

    for feeder in feeders:
        current_ts = current_ts + timedelta(seconds=rng.randint(120, 3_600))
        small_amt  = lognormal_amount(rng, mu=5.5, sigma=0.6, lo=100.0, hi=3_000.0)
        total_collected += small_amt
        tx.append(make_transaction(rng, feeder, aggregator, small_amt,
                                   current_ts, "mule_flow",
                                   channel_override=_mule_channel(rng)))

    disperse_start = current_ts + timedelta(hours=rng.randint(1, 12))
    current_ts     = disperse_start
    share          = round(total_collected / n_exits, 2)

    for exit_acc in exits:
        current_ts = current_ts + timedelta(seconds=rng.randint(60, 900))
        jitter     = round(rng.uniform(-100.0, 100.0), 2)
        exit_amt   = max(1.0, share + jitter)
        tx.append(make_transaction(rng, aggregator, exit_acc, exit_amt,
                                   current_ts, "mule_flow",
                                   channel_override=_mule_channel(rng)))
    return tx


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_PATTERN_MAP: dict[str, Callable] = {
    "linear":   _linear_chain,
    "star":     _star_chain,
    "circular": _circular_chain,
    "funnel":   _funnel_chain,
}


def generate_fraud_transactions(
    pattern: str,
    mule_ids: list[str],
    normal_ids: list[str],
    n_chains: int,
    rng: random.Random,
) -> tuple[list[Transaction], int]:
    """
    Generate fraud transactions for the requested pattern.

    Returns (transactions, chains_successfully_built).
    Unknown patterns fall back to 'linear' with a warning.
    """
    builder = _PATTERN_MAP.get(pattern)
    if builder is None:
        print(f"  [WARN] Unknown pattern '{pattern}', falling back to 'linear'.")
        builder = _linear_chain

    all_tx: list[Transaction] = []
    built = 0
    for _ in range(n_chains):
        chain = builder(mule_ids, normal_ids, rng)
        if chain:
            all_tx.extend(chain)
            built += 1
    return all_tx, built
