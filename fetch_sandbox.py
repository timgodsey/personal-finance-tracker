import os
import datetime
import time  # <-- Added this
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.products import Products
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest

# Load the keys
load_dotenv()

# Setup Client
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': os.getenv('PLAID_CLIENT_ID'),
        'secret': os.getenv('PLAID_SECRET'),
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

try:
    # 1. Generate a Sandbox Public Token
    print("🏦 Generating fake bank login...")
    pt_request = SandboxPublicTokenCreateRequest(
        institution_id="ins_109508", 
        initial_products=[Products("transactions")]
    )
    pt_response = client.sandbox_public_token_create(pt_request)
    public_token = pt_response['public_token']

    # 2. Exchange for an Access Token
    print("🔑 Exchanging for Access Token...")
    exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
    exchange_response = client.item_public_token_exchange(exchange_request)
    access_token = exchange_response['access_token']

    # --- THE FIX ---
    print("⏳ Giving Plaid 10 seconds to generate the sandbox data...")
    time.sleep(10) 
    # ---------------

    # 3. Fetch Transactions
    print("📊 Fetching Transactions...\n")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
    end_date = datetime.datetime.now().date()

    tx_request = TransactionsGetRequest(
        access_token=access_token,
        start_date=start_date,
        end_date=end_date
    )
    tx_response = client.transactions_get(tx_request)

    # 4. Print the results
    transactions = tx_response['transactions']
    
    print("-" * 50)
    for tx in transactions:
        print(f"{tx['date']} | {tx['name'][:25]:<25} | ${tx['amount']}")
    print("-" * 50)
    print(f"Total records found: {len(transactions)}")

except plaid.ApiException as e:
    print(f"❌ Plaid API Error: {e.body}")
except Exception as e:
    print(f"❌ General Error: {e}")