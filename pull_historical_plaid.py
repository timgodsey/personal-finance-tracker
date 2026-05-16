import os
import json
import sqlite3
from datetime import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from dotenv import load_dotenv
from openai import OpenAI

# --- CONFIGURATION ---
client = OpenAI(
    base_url="http://localhost:11434/v1", 
    api_key="ollama" 
)

system_prompt = """You are an expert financial categorizer. I run a fabrication, 3D printing, and electronics business called Godsey Fabrications. 
Analyze the following bank transaction and categorize it.
Buckets: 'Definitely Business', 'Maybe Business', 'Definitely Personal'.
Output ONLY valid JSON with keys: "category", and "justification". No markdown formatting."""

def setup_database():
    conn = sqlite3.connect('finances.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            name TEXT,
            amount TEXT,
            ai_category TEXT,
            ai_justification TEXT,
            user_status TEXT DEFAULT 'Pending Review',
            final_category TEXT,
            notes TEXT,
            account_id TEXT,
            transaction_id TEXT UNIQUE
        )
    ''')
    conn.commit()
    return conn

def fetch_historical_data():
    load_dotenv()
    access_token = os.getenv("PLAID_ACCESS_TOKEN")
    
    if not access_token:
        print(" Error: PLAID_ACCESS_TOKEN not found in .env file.")
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
    plaid_client = plaid_api.PlaidApi(api_client)

    print("️  Setting up database...")
    db_conn = setup_database()
    cursor = db_conn.cursor()

    print(" Fetching historical data from Plaid...")

    # Fetch from Jan 1, 2026
    start_date = datetime(2026, 1, 1).date()
    end_date = datetime.now().date()
    
    try:
        options = TransactionsGetRequestOptions()
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=options
        )
        response = plaid_client.transactions_get(request)
        transactions = response['transactions']
        
        # Paginate to get all transactions
        while len(transactions) < response['total_transactions']:
            options = TransactionsGetRequestOptions(
                offset=len(transactions)
            )
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=options
            )
            response = plaid_client.transactions_get(request)
            transactions.extend(response['transactions'])
            
        print(f" Fetched {len(transactions)} historical transactions!")
        print("-" * 50)
        
        for i, tx in enumerate(transactions):
            tx_id = tx.get('transaction_id')
            date = tx.get('date')
            name = tx.get('name')
            amount = str(tx.get('amount'))
            account_id = tx.get('account_id')
            
            print(f"\n[{i+1}/{len(transactions)}] [{date}] {name[:40]} - ${amount}")
            
            cursor.execute("SELECT id FROM transactions WHERE transaction_id = ?", (tx_id,))
            if cursor.fetchone():
                print("    Already in database, skipping...")
                continue
                
            print("    Asking Qwen to categorize...")
            
            try:
                completion = client.chat.completions.create(
                    model="qwen3:8b",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Transaction Name: {name}\nAmount: {amount}\nDate: {date}"}
                    ],
                    temperature=0.1
                )
                
                ai_response = completion.choices[0].message.content
                clean_json = ai_response.replace('```json', '').replace('```', '').strip()
                
                ai_data = json.loads(clean_json)
                category = ai_data.get('category', 'Error parsing')
                justification = ai_data.get('justification', 'Error parsing')
                
                print(f"   -> Result: {category}")
                
                cursor.execute('''
                    INSERT INTO transactions (date, name, amount, ai_category, ai_justification, account_id, transaction_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (date, name, amount, category, justification, account_id, tx_id))
                db_conn.commit()
                print("    Saved to finances.db")
                
            except Exception as e:
                print(f"    Failed to process: {e}")
                
        db_conn.close()
        print("\n Historical Plaid pipeline complete!")
        
    except plaid.ApiException as e:
        print(f" Failed to fetch transactions: {e.body}")

if __name__ == "__main__":
    fetch_historical_data()
