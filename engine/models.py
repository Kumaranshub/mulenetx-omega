"""
engine/models.py
----------------
Shared domain models and schema constants for the MuleNet-X Omega pipeline.

All modules import from here so the data contract stays in one place.
Adding or renaming a field means editing exactly this file.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Literal

FraudPattern = Literal["linear", "star", "circular", "funnel"]

ACCOUNT_FIELDS = [
    "account_id", "created_at", "account_type", "is_mule",
]

TRANSACTION_FIELDS = [
    "from_account", "to_account", "amount", "timestamp",
    "label", "device_id", "channel", "region",
]

FEATURE_FIELDS = [
    "account_id", "account_type", "is_mule",
    "in_degree", "out_degree", "total_in", "total_out",
    "velocity_score", "imbalance_score",
]

RISK_FIELDS = ["account_id", "risk_score"]

CHANNELS        = ["mobile", "web", "atm"]
CHANNEL_WEIGHTS = [0.55, 0.35, 0.10]
REGIONS         = ["US-WEST", "US-EAST", "EU-WEST", "EU-EAST", "APAC", "LATAM"]


@dataclass(frozen=True)
class SimConfig:
    """Immutable run configuration. Every experiment derives from this."""
    total_accounts:     int          = 500
    mule_pct:           float        = 0.08
    business_pct:       float        = 0.10
    total_transactions: int          = 3000
    seed:               int          = 42
    out_dir:            str          = "."
    stream:             bool         = False
    fraud_pattern:      FraudPattern = "linear"
    snapshot_days:      int          = 0


@dataclass(frozen=True)
class SimWindow:
    """Defines the simulation time boundary shared across all generators."""
    start: datetime = datetime(2024, 1, 1)
    days:  int      = 180

    @property
    def end(self) -> datetime:
        return self.start + timedelta(days=self.days)


WINDOW = SimWindow()


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
