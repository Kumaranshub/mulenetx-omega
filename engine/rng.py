"""
engine/rng.py
-------------
Stateless RNG primitives used by every generator in the pipeline.

All functions accept an explicit `random.Random` instance rather than using
the global random state, so multiple experiments can run independently with
full reproducibility.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

try:
    import numpy as _np
    _NUMPY = True
except ImportError:
    _NUMPY = False

from engine.models import (
    Transaction, CHANNELS, CHANNEL_WEIGHTS, REGIONS, SimWindow,
)

WINDOW = SimWindow()


def seed_all(seed: int) -> random.Random:
    """
    Seed both the global `random` module and numpy (if available), then
    return a private `random.Random` instance for caller-controlled RNG.
    """
    random.seed(seed)
    if _NUMPY:
        _np.random.seed(seed)
    return random.Random(seed)


def lognormal_amount(
    rng: random.Random, mu: float, sigma: float, lo: float, hi: float
) -> float:
    """Draw an amount from a log-normal distribution clipped to [lo, hi]."""
    return round(max(lo, min(rng.lognormvariate(mu, sigma), hi)), 2)


def pick_channel(
    rng: random.Random,
    channels: list[str] = CHANNELS,
    weights: list[float] = CHANNEL_WEIGHTS,
) -> str:
    return rng.choices(channels, weights=weights, k=1)[0]


def new_device_id(rng: random.Random) -> str:
    return "DEV-" + format(rng.getrandbits(48), "012x").upper()


def new_account_id(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128)))


def clamp_ts(ts: datetime) -> datetime:
    return min(ts, WINDOW.end)


def make_transaction(
    rng: random.Random,
    sender: str,
    receiver: str,
    amount: float,
    ts: datetime,
    label: str,
    channel_override: Optional[str] = None,
) -> Transaction:
    """
    Central transaction factory — every generator calls this so the schema
    stays consistent regardless of which fraud pattern is active.
    """
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
