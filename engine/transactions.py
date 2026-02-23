"""
engine/transactions.py
----------------------
Legitimate transaction generators for normal and business accounts.

Fraud pattern generators (mule chains, star, circular, funnel) live in
engine/patterns.py and are dispatched at runtime by the experiment runner.
"""

import random
from datetime import timedelta

from engine.models import Transaction, WINDOW
from engine.rng import lognormal_amount, make_transaction

BURST_PROBABILITY  = 0.05
BURST_CLUSTER_SIZE = (3, 8)


def generate_normal_transactions(
    normal_ids: list[str],
    all_ids: list[str],
    target: int,
    rng: random.Random,
) -> list[Transaction]:
    """
    Simulate retail user behaviour: infrequent, variable amounts, evening-biased
    timing, with occasional burst clusters (shopping sprees).
    """
    if not normal_ids or target == 0:
        return []

    tx: list[Transaction] = []
    i = 0

    while i < target:
        sender   = rng.choice(normal_ids)
        receiver = rng.choice([a for a in all_ids if a != sender])
        ts = WINDOW.start + timedelta(
            days=rng.randint(0, WINDOW.days - 1),
            hours=int(rng.triangular(6, 23, 19)),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )
        amount = lognormal_amount(rng, mu=4.5, sigma=1.2, lo=1.0, hi=5_000.0)
        tx.append(make_transaction(rng, sender, receiver, amount,
                                   min(ts, WINDOW.end), "normal"))
        i += 1

        if rng.random() < BURST_PROBABILITY and i < target:
            burst_n = rng.randint(*BURST_CLUSTER_SIZE)
            for _ in range(min(burst_n, target - i)):
                rx       = rng.choice([a for a in all_ids if a != sender])
                burst_ts = min(ts + timedelta(seconds=rng.randint(30, 1_800)), WINDOW.end)
                burst_amt = lognormal_amount(rng, mu=4.2, sigma=0.9, lo=1.0, hi=2_000.0)
                tx.append(make_transaction(rng, sender, rx, burst_amt, burst_ts, "normal"))
                i += 1

    return tx


def generate_business_transactions(
    business_ids: list[str],
    all_ids: list[str],
    target: int,
    rng: random.Random,
) -> list[Transaction]:
    """
    Simulate corporate payment behaviour: working-hours timestamps, moderate
    amounts, predominantly web channel.
    """
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
        channel = rng.choices(["web", "mobile", "atm"], weights=[0.70, 0.28, 0.02], k=1)[0]
        tx.append(make_transaction(rng, sender, receiver, amount,
                                   min(ts, WINDOW.end), "normal",
                                   channel_override=channel))
    return tx
