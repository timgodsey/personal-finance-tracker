import requests
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

def fetch_historical_data():
    load_dotenv()
    access_url = os.getenv("SIMPLEFIN_ACCESS_URL")
    
    if not access_url:
        print("❌ Error: SIMPLEFIN_ACCESS_URL not found in .env file.")
        print("Please run setup_simplefin.py first to claim your token.")
        return

    try:
        scheme, rest = access_url.split('//', 1)
        auth, rest = rest.split('@', 1)
        url = f"{scheme}//{rest}/accounts"
        username, password = auth.split(':', 1)
    except ValueError:
        print("❌ Error: SIMPLEFIN_ACCESS_URL format is invalid.")
        return

    # Target start and end dates
    # Jan 1, 2026 to current UTC time
    current_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    final_end = datetime.now(timezone.utc)
    
    all_accounts = {}
    
    print(f"📊 Fetching historical data from SimpleFIN...")
    print(f"   Note: SimpleFIN limits fetches to 90 days at a time. We will batch this automatically.\n")

    while current_start < final_end:
        # SimpleFIN allows up to 90 days per request. We'll use 89 to be safe.
        current_end = min(current_start + timedelta(days=89), final_end)
        
        start_ts = int(current_start.timestamp())
        end_ts = int(current_end.timestamp())
        
        print(f"   ↳ Fetching {current_start.date()} to {current_end.date()}")
        
        params = {
            'version': '2',
            'start-date': start_ts,
            'end-date': end_ts
        }
        
        response = requests.get(url, auth=(username, password), params=params)
        
        if response.status_code == 200:
            data = response.json()
            # Merge logic
            for acc in data.get("accounts", []):
                acc_id = acc.get("id")
                if acc_id not in all_accounts:
                    all_accounts[acc_id] = acc
                else:
                    # Append new transactions to existing account
                    existing_tx = all_accounts[acc_id].setdefault("transactions", [])
                    new_tx = acc.get("transactions", [])
                    existing_tx.extend(new_tx)
        else:
            print(f"❌ Failed to fetch data: {response.status_code} {response.text}")
            break
            
        # Move the start date to right after the end of this batch
        current_start = current_end + timedelta(seconds=1)

    # Format the merged data back into the expected structure
    merged_data = {"accounts": list(all_accounts.values())}
    
    with open("simplefin_historical.json", "w") as f:
        json.dump(merged_data, f, indent=4)
    
    print(f"\n✅ Historical data merged and saved to simplefin_historical.json.")
    
    # Summary
    total_tx = 0
    print("-" * 50)
    for acc in merged_data.get("accounts", []):
        tx_count = len(acc.get("transactions", []))
        total_tx += tx_count
        print(f"Account: {acc.get('name', 'Unknown')} | Total Transactions: {tx_count}")
    print("-" * 50)
    print(f"🎉 Total transactions downloaded across all accounts: {total_tx}")

if __name__ == "__main__":
    fetch_historical_data()
