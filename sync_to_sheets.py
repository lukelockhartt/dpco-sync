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


def get_existing_transactions(sheet):
    """Return (existing_ids, pending_row_map).

    existing_ids     – set of transaction_ids already in the sheet.
    pending_row_map  – {transaction_id: 1-based_row_number} for every row
                       whose Pending column is still "True". Used to update
                       those rows in place when the transaction clears.
    """
    all_values = sheet.get_all_values()
    if len(all_values) <= 1:
        return set(), {}

    existing_ids = set()
    pending_row_map = {}

    for i, row in enumerate(all_values[1:], start=2):  # row 1 is the header
        txn_id = row[7] if len(row) > 7 else ""
        if txn_id:
            existing_ids.add(txn_id)
            if len(row) > 6 and row[6] == "True":
                pending_row_map[txn_id] = i

    return existing_ids, pending_row_map


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

    existing_ids, pending_row_map = get_existing_transactions(sheet)
    print(f"  {len(existing_ids)} already in sheet ({len(pending_row_map)} still pending)")

    new_rows = []
    rows_to_update = []  # list of (1-based row number, row data)

    for txn in transactions:
        txn_id = txn.get("transaction_id")
        pending_txn_id = txn.get("pending_transaction_id")  # set by Plaid when a pending txn posts

        if txn_id in existing_ids:
            continue

        if pending_txn_id and pending_txn_id in pending_row_map:
            # This posted transaction replaces an existing pending row — update it.
            rows_to_update.append((pending_row_map[pending_txn_id], build_row(txn)))
        else:
            new_rows.append(build_row(txn))

    if rows_to_update:
        for row_num, row_data in rows_to_update:
            sheet.update(f"A{row_num}:H{row_num}", [row_data], value_input_option="USER_ENTERED")
        print(f"updated {len(rows_to_update)} pending → posted transactions")

    if not new_rows:
        if not rows_to_update:
            print("nothing new to add")
        return

    new_rows.sort(key=lambda r: r[0])
    sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
    print(f"added {len(new_rows)} new transactions")


if __name__ == "__main__":
    main()
