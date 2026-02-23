import csv
import uuid
import random
import argparse
from datetime import datetime, timedelta

DEFAULT_TOTAL_ACCOUNTS    = 500
DEFAULT_MULE_PCT          = 0.08   # 8% of accounts are mules
DEFAULT_BUSINESS_PCT      = 0.10   # 10% of accounts are business
DEFAULT_TOTAL_TRANSACTIONS = 3000
DEFAULT_RANDOM_SEED       = 42
DEFAULT_ACCOUNTS_FILE     = "accounts.csv"
DEFAULT_TRANSACTIONS_FILE = "transactions.csv"

# Simulation window: transactions span this many days from START_DATE
SIM_START_DATE = datetime(2024, 1, 1)
SIM_DAYS       = 180

def generate_accounts(
    total_accounts: int,
    mule_pct: float,
    business_pct: float,
    rng: random.Random,
) -> list[dict]:
    
    n_mules    = max(2, int(total_accounts * mule_pct))
    n_business = max(2, int(total_accounts * business_pct))
    n_normal   = total_accounts - n_mules - n_business

    accounts = []

    def _make_account(account_type: str) -> dict:
        # Accounts are opened at a random point within the simulation window
        days_offset = rng.randint(0, SIM_DAYS - 1)
        created_at  = SIM_START_DATE + timedelta(days=days_offset)
        return {
            "account_id":   str(uuid.UUID(int=rng.getrandbits(128))),
            "created_at":   created_at.strftime("%Y-%m-%d"),
            "account_type": account_type,
        }

    for _ in range(n_normal):
        accounts.append(_make_account("normal"))
    for _ in range(n_business):
        accounts.append(_make_account("business"))
    for _ in range(n_mules):
        accounts.append(_make_account("mule"))

    rng.shuffle(accounts)
    return accounts

def _random_timestamp(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """Return a random datetime between start and end."""
    delta   = end - start
    seconds = int(delta.total_seconds())
    return start + timedelta(seconds=rng.randint(0, seconds))


def _accounts_by_type(accounts: list[dict]) -> dict[str, list[str]]:
    """Return a dict mapping account_type -> list of account_ids."""
    by_type: dict[str, list[str]] = {"normal": [], "business": [], "mule": []}
    for acc in accounts:
        by_type[acc["account_type"]].append(acc["account_id"])
    return by_type



def generate_normal_transactions(
    normal_ids: list[str],
    all_ids: list[str],
    n_transactions: int,
    rng: random.Random,
) -> list[dict]:
   
    if not normal_ids or n_transactions == 0:
        return []

    sim_end  = SIM_START_DATE + timedelta(days=SIM_DAYS)
    tx_list  = []

    for _ in range(n_transactions):
        sender   = rng.choice(normal_ids)
        receiver = rng.choice(all_ids)
        # Avoid self-loops
        while receiver == sender:
            receiver = rng.choice(all_ids)

        # Log-normal gives realistic retail spend distribution
        amount    = round(rng.lognormvariate(mu=4.5, sigma=1.2), 2)
        amount    = max(1.00, min(amount, 5000.00))
        timestamp = _random_timestamp(rng, SIM_START_DATE, sim_end)

        tx_list.append({
            "from_account": sender,
            "to_account":   receiver,
            "amount":       amount,
            "timestamp":    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return tx_list


def generate_business_transactions(
    business_ids: list[str],
    all_ids: list[str],
    n_transactions: int,
    rng: random.Random,
) -> list[dict]:
    
    if not business_ids or n_transactions == 0:
        return []

    sim_end  = SIM_START_DATE + timedelta(days=SIM_DAYS)
    tx_list  = []

    for _ in range(n_transactions):
        sender   = rng.choice(business_ids)
        receiver = rng.choice(all_ids)
        while receiver == sender:
            receiver = rng.choice(all_ids)

        base_day  = rng.randint(0, SIM_DAYS - 1)
        hour      = int(rng.triangular(8, 20, 13))   
        minute    = rng.randint(0, 59)
        timestamp = SIM_START_DATE + timedelta(days=base_day, hours=hour, minutes=minute)
        timestamp = min(timestamp, sim_end)

        # Moderate amounts: normally distributed around $500
        amount = round(abs(rng.normalvariate(mu=500, sigma=300)), 2)
        amount = max(10.00, min(amount, 10000.00))

        tx_list.append({
            "from_account": sender,
            "to_account":   receiver,
            "amount":       amount,
            "timestamp":    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return tx_list

def generate_mule_chains(
    mule_ids: list[str],
    normal_ids: list[str],
    n_chains: int,
    rng: random.Random,
) -> tuple[list[dict], int]:
    
    if len(mule_ids) < 2 or n_chains == 0:
        return [], 0

    tx_list       = []
    chains_created = 0

    # Reserve a few mules as permanent hub nodes (shared across chains)
    n_hubs   = max(1, len(mule_ids) // 5)
    hub_mules = mule_ids[:n_hubs]
    leaf_mules = mule_ids[n_hubs:]

    for _ in range(n_chains):
    
        max_start_offset = SIM_DAYS * 24 * 3600 - 7200   # leave 2 h buffer
        chain_start = SIM_START_DATE + timedelta(
            seconds=rng.randint(0, max(1, max_start_offset))
        )

    
        chain_len = rng.randint(3, 7)

      
        use_hub = (len(leaf_mules) >= 2) and rng.random() < 0.6
        if use_hub:
            hub         = rng.choice(hub_mules)
            if len(leaf_mules) >= chain_len - 1:
                chain_nodes = rng.sample(leaf_mules, chain_len - 1)
            else:
                chain_nodes = rng.choices(leaf_mules, k=chain_len - 1)
            mid = len(chain_nodes) // 2
            chain_nodes.insert(mid, hub)
        else:
            if len(mule_ids) >= chain_len:
                chain_nodes = rng.sample(mule_ids, chain_len)
            else:
                chain_nodes = rng.choices(mule_ids, k=chain_len)

        
        entry_amount = round(rng.uniform(5000, 50000), 2)
        if normal_ids:
            entry_sender = rng.choice(normal_ids)
        else:
          
            entry_sender = chain_nodes[-1]

        current_time   = chain_start
        current_amount = entry_amount

        tx_list.append({
            "from_account": entry_sender,
            "to_account":   chain_nodes[0],
            "amount":       current_amount,
            "timestamp":    current_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

       
        for i in range(len(chain_nodes) - 1):
            sender   = chain_nodes[i]
            receiver = chain_nodes[i + 1]

            
            gap_seconds  = rng.randint(30, 900)
            current_time = current_time + timedelta(seconds=gap_seconds)

            fee_pct        = rng.uniform(0.01, 0.03)
            current_amount = round(current_amount * (1 - fee_pct), 2)

            jitter          = round(rng.uniform(-0.50, 0.50), 2)
            current_amount  = max(1.00, current_amount + jitter)

            tx_list.append({
                "from_account": sender,
                "to_account":   receiver,
                "amount":       current_amount,
                "timestamp":    current_time.strftime("%Y-%m-%d %H:%M:%S"),
            })

        chains_created += 1

    return tx_list, chains_created



def write_csv(filepath: str, fieldnames: list[str], rows: list[dict]) -> None:
    """
    Write a list of dicts to a CSV file with a header row.

    Args:
        filepath:   Destination file path.
        fieldnames: Ordered list of column names (CSV header).
        rows:       Data rows; each dict must contain all fieldnames.
    """
    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



def print_summary(
    accounts: list[dict],
    transactions: list[dict],
    n_chains: int,
) -> None:
    """Print a structured summary of the generated dataset to stdout."""
    by_type = _accounts_by_type(accounts)
    total   = len(accounts)

    print("\n" + "=" * 50)
    print("  Synthetic Data Generation — Summary")
    print("=" * 50)
    print(f"  Accounts total  : {total:>6,}")
    print(f"    Normal        : {len(by_type['normal']):>6,}  "
          f"({100*len(by_type['normal'])/total:.1f}%)")
    print(f"    Business      : {len(by_type['business']):>6,}  "
          f"({100*len(by_type['business'])/total:.1f}%)")
    print(f"    Mule          : {len(by_type['mule']):>6,}  "
          f"({100*len(by_type['mule'])/total:.1f}%)")
    print(f"\n  Transactions    : {len(transactions):>6,}")
    print(f"  Mule chains     : {n_chains:>6,}")
    print("=" * 50 + "\n")


def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments, falling back to module-level defaults."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic financial transaction data for fraud detection."
    )
    parser.add_argument(
        "--accounts", type=int, default=DEFAULT_TOTAL_ACCOUNTS,
        help=f"Total number of accounts (default: {DEFAULT_TOTAL_ACCOUNTS})"
    )
    parser.add_argument(
        "--mule-pct", type=float, default=DEFAULT_MULE_PCT,
        help=f"Fraction of accounts that are mules (default: {DEFAULT_MULE_PCT})"
    )
    parser.add_argument(
        "--business-pct", type=float, default=DEFAULT_BUSINESS_PCT,
        help=f"Fraction of accounts that are businesses (default: {DEFAULT_BUSINESS_PCT})"
    )
    parser.add_argument(
        "--transactions", type=int, default=DEFAULT_TOTAL_TRANSACTIONS,
        help=f"Total number of transactions to generate (default: {DEFAULT_TOTAL_TRANSACTIONS})"
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_RANDOM_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_RANDOM_SEED})"
    )
    parser.add_argument(
        "--accounts-file", default=DEFAULT_ACCOUNTS_FILE,
        help=f"Output path for accounts CSV (default: {DEFAULT_ACCOUNTS_FILE})"
    )
    parser.add_argument(
        "--transactions-file", default=DEFAULT_TRANSACTIONS_FILE,
        help=f"Output path for transactions CSV (default: {DEFAULT_TRANSACTIONS_FILE})"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng  = random.Random(args.seed)

    print(f"[1/5] Generating {args.accounts:,} accounts …")
    accounts = generate_accounts(
        total_accounts=args.accounts,
        mule_pct=args.mule_pct,
        business_pct=args.business_pct,
        rng=rng,
    )
    by_type  = _accounts_by_type(accounts)
    all_ids  = [a["account_id"] for a in accounts]

    
    n_mule_chains = max(1, len(by_type["mule"]) // 3)
    mule_tx_budget = n_mule_chains * 5   

    remaining_tx = max(0, args.transactions - mule_tx_budget)
    n_business_tx = int(remaining_tx * 0.40)
    n_normal_tx   = remaining_tx - n_business_tx

    print(f"[2/5] Generating {n_normal_tx:,} normal transactions …")
    normal_tx = generate_normal_transactions(
        normal_ids=by_type["normal"],
        all_ids=all_ids,
        n_transactions=n_normal_tx,
        rng=rng,
    )

    print(f"[3/5] Generating {n_business_tx:,} business transactions …")
    business_tx = generate_business_transactions(
        business_ids=by_type["business"],
        all_ids=all_ids,
        n_transactions=n_business_tx,
        rng=rng,
    )

    print(f"[4/5] Generating {n_mule_chains} mule chains …")
    mule_tx, chains_created = generate_mule_chains(
        mule_ids=by_type["mule"],
        normal_ids=by_type["normal"],
        n_chains=n_mule_chains,
        rng=rng,
    )

    # Combine and shuffle all transactions so the CSV isn't ordered by type
    all_transactions = normal_tx + business_tx + mule_tx
    rng.shuffle(all_transactions)

    print(f"[5/5] Writing CSV files …")
    write_csv(
        filepath=args.accounts_file,
        fieldnames=["account_id", "created_at", "account_type"],
        rows=accounts,
    )
    write_csv(
        filepath=args.transactions_file,
        fieldnames=["from_account", "to_account", "amount", "timestamp"],
        rows=all_transactions,
    )

    print(f"  → {args.accounts_file}")
    print(f"  → {args.transactions_file}")

    print_summary(accounts, all_transactions, chains_created)


if __name__ == "__main__":
    main()
