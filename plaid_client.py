import os
from datetime import date, timedelta
from dotenv import load_dotenv

import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

load_dotenv()

def get_plaid_client() -> plaid_api.PlaidApi:
    configuration = plaid.Configuration(
        host=plaid.Environment.Production,
        api_key={
            "clientId": os.environ["PLAID_CLIENT_ID"].strip(),
            "secret": os.environ["PLAID_SECRET"].strip(),
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def fetch_transactions(days: int = 30) -> list[dict]:
    client = get_plaid_client()
    access_token = os.environ["PLAID_ACCESS_TOKEN"].strip()

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    all_transactions = []
    offset = 0
    PAGE_SIZE = 500

    while True:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                count=PAGE_SIZE,
                offset=offset,
            ),
        )
        response = client.transactions_get(request)
        transactions = response["transactions"]
        all_transactions.extend(transactions)

        # Break when Plaid returns a short page (genuine end of results) or when
        # we have reached the reported total. Using both conditions guards against
        # total_transactions excluding pending entries on some institutions.
        if len(transactions) < PAGE_SIZE or len(all_transactions) >= response["total_transactions"]:
            break
        offset += len(transactions)

    return all_transactions
