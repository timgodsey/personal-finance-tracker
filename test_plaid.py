import os
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api

# Load the keys from the .env file
load_dotenv()

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')

# Configure the Plaid client for the Sandbox environment
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

print("✅ Plaid client successfully initialized and ready for data requests!")