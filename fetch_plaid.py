import os
import json
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from dotenv import load_dotenv

def fetch_data():
    load_dotenv()
    access_token = os.getenv("PLAID_ACCESS_TOKEN")
    
    if not access_token:
        print("❌ Error: PLAID_ACCESS_TOKEN not found in .env file.")
        print("Please run setup_plaid.py first to link your bank.")
        return

    PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
    PLAID_SECRET = os.getenv('PLAID_SECRET')
    PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

    if PLAID_ENV == 'sandbox':
        host = plaid.Environment.Sandbox
    elif PLAID_ENV == 'development':
        host = plaid.Environment.Development
    else:
        host = plaid.Environment.Production

    configuration = plaid.Configuration(
        host=host,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
        }
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    print("📊 Fetching data from Plaid...")
    
    try:
        request = AccountsGetRequest(access_token=access_token)
        response = client.accounts_get(request)
        
        # Convert response to dictionary
        data = response.to_dict()
        
        # Save to a local cache file
        with open("plaid_cache.json", "w") as f:
            json.dump(data, f, indent=4, default=str)
        
        print(f"✅ Data fetched successfully! Saved to plaid_cache.json.")
        
        # Basic summary
        accounts = data.get("accounts", [])
        print("-" * 50)
        for acc in accounts:
            balance = acc.get('balances', {}).get('current', '0.00')
            currency = acc.get('balances', {}).get('iso_currency_code', 'USD')
            name = acc.get('name', 'Unknown')
            print(f"Account: {name} | Balance: {balance} {currency}")
        print("-" * 50)
    except plaid.ApiException as e:
        print(f"❌ Failed to fetch data: {e.body}")

if __name__ == "__main__":
    fetch_data()
