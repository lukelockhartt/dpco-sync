#!/usr/bin/env python3

import argparse
import csv
import os
from datetime import datetime
from plaid_client import fetch_transactions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    print(f"fetching last {args.days} days...")

    transactions = fetch_transactions(days=args.days)

    if not transactions:
        print("no transactions found")
        return

    output_file = os.path.join(os.path.dirname(__file__), "transactions.csv")
    fieldnames = ["date", "name", "merchant_name", "amount", "category", "account_id", "transaction_id"]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for txn in transactions:
            category = txn.get("category")
            writer.writerow({
                "date": txn["date"],
                "name": txn["name"],
                "merchant_name": txn.get("merchant_name") or "",
                "amount": txn["amount"],
                "category": " > ".join(category) if category else "",
                "account_id": txn["account_id"],
                "transaction_id": txn["transaction_id"],
            })

    print(f"saved {len(transactions)} transactions to {output_file}")


if __name__ == "__main__":
    main()
