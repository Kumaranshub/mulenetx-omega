"""
engine/accounts.py
------------------
Account generation for the MuleNet-X Omega simulation.

Responsible only for creating Account records and partitioning them by type.
Transaction generation is handled in engine/transactions.py and engine/patterns.py.
"""

import random
from datetime import timedelta

from engine.models import Account, SimConfig, WINDOW
from engine.rng import new_account_id


def generate_accounts(cfg: SimConfig, rng: random.Random) -> list[Account]:
    """
    Create shuffled account records for all three behavioural groups.

    Account counts are derived from cfg percentages; minimums of 2 per group
    are enforced so downstream generators always have at least one sender and
    one receiver to work with.
    """
    n_mules    = max(2, int(cfg.total_accounts * cfg.mule_pct))
    n_business = max(2, int(cfg.total_accounts * cfg.business_pct))
    n_normal   = cfg.total_accounts - n_mules - n_business

    def build(account_type: str) -> Account:
        created_at = WINDOW.start + timedelta(days=rng.randint(0, WINDOW.days - 1))
        return Account(
            account_id=new_account_id(rng),
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
    """Return a mapping from account_type to a list of account_ids."""
    groups: dict[str, list[str]] = {"normal": [], "business": [], "mule": []}
    for acc in accounts:
        groups[acc.account_type].append(acc.account_id)
    return groups
