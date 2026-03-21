#!/usr/bin/env python3

import argparse
import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

from plaid_client import fetch_transactions

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER = ["Date", "Name", "Merchant", "Amount", "Category", "Channel", "Pending", "Transaction ID"]


def get_sheet():
    creds_file = os.environ["GOOGLE_CREDENTIALS_FILE"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]

    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).sheet1


def ensure_header(sheet):
    existing = sheet.row_values(1)
    if existing != HEADER:
        if not existing:
            sheet.append_row(HEADER, value_input_option="RAW")
        else:
            sheet.update("A1", [HEADER])


def get_existing_ids(sheet):
    # skip header row, pull transaction ids from column h
    all_values = sheet.get_all_values()
    if len(all_values) <= 1:
        return set()
    return {row[7] for row in all_values[1:] if len(row) > 7 and row[7]}


def build_row(txn) -> list:
    category = txn.get("category") or []
    category_str = " > ".join(category) if category else ""
    channel = txn.get("payment_channel") or ""

    return [
        str(txn.get("date", "")),
        txn.get("name") or "",
        txn.get("merchant_name") or "",
        txn.get("amount", ""),
        category_str,
        channel,
        str(txn.get("pending", False)),
        txn.get("transaction_id") or "",
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    print(f"fetching last {args.days} days from plaid...")
    transactions = fetch_transactions(days=args.days)
    print(f"  got {len(transactions)} transactions")

    print("connecting to google sheets...")
    sheet = get_sheet()
    ensure_header(sheet)

    existing_ids = get_existing_ids(sheet)
    print(f"  {len(existing_ids)} already in sheet")

    new_rows = [
        build_row(txn)
        for txn in transactions
        if txn.get("transaction_id") not in existing_ids
    ]

    if not new_rows:
        print("nothing new to add")
        return

    new_rows.sort(key=lambda r: r[0])
    sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
    print(f"added {len(new_rows)} new transactions")


if __name__ == "__main__":
    main()
