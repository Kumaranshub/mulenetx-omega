import json
import statistics
with open("data/transactions.json") as f:
    txns = json.load(f)
amounts = [t["amount"] for t in txns]
mean = statistics.mean(amounts)
stdev = statistics.stdev(amounts)
for txn in txns:
    z = (txn["amount"] - mean) / stdev
    if z > 2.5:
        print("Anomaly detected:", txn["id"])
