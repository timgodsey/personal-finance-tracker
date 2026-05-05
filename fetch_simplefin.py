import requests
import os
import json
from dotenv import load_dotenv

def fetch_data():
    load_dotenv()
    access_url = os.getenv("SIMPLEFIN_ACCESS_URL")
    
    if not access_url:
        print("❌ Error: SIMPLEFIN_ACCESS_URL not found in .env file.")
        print("Please run setup_simplefin.py first to claim your token.")
        return

    # Strip out the auth details from the access URL to use standard Basic Auth
    try:
        scheme, rest = access_url.split('//', 1)
        auth, rest = rest.split('@', 1)
        url = f"{scheme}//{rest}/accounts"
        username, password = auth.split(':', 1)
    except ValueError:
        print("❌ Error: SIMPLEFIN_ACCESS_URL format is invalid.")
        return

    print("📊 Fetching data from SimpleFIN...")
    # Grab your data
    response = requests.get(url, auth=(username, password), params={'version':'2'})
    
    if response.status_code == 200:
        data = response.json()
        
        # Save to a local cache file to avoid rate limits
        with open("simplefin_cache.json", "w") as f:
            json.dump(data, f, indent=4)
        
        print(f"✅ Data fetched successfully! Saved to simplefin_cache.json.")
        
        # Basic summary
        accounts = data.get("accounts", [])
        print("-" * 50)
        for acc in accounts:
            print(f"Account: {acc.get('name', 'Unknown')} | Balance: {acc.get('balance', '0.00')} {acc.get('currency', 'USD')}")
        print("-" * 50)
        print("ℹ️  Note: SimpleFIN only syncs once roughly every 24 hours.")
        print("We are caching the data locally to respect rate limits.")
    else:
        print(f"❌ Failed to fetch data: {response.status_code} {response.text}")

if __name__ == "__main__":
    fetch_data()
