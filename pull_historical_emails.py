import os
import json
import sqlite3
import email.utils
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI

# --- CONFIGURATION ---
client = OpenAI(
    base_url="http://localhost:11434/v1", 
    api_key="ollama" # api_key is required by the client but ignored by ollama
)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

system_prompt = """You are an expert financial categorizer. I run a fabrication, 3D printing, and electronics business called Godsey Fabrications. 
Analyze the following receipt text and categorize it.
Buckets: 'Definitely Business', 'Maybe Business', 'Definitely Personal'.
Output ONLY valid JSON with keys: "category", "justification", and "amount". Extract the total transaction amount (e.g. "$124.50") for the "amount" field, or "Unknown" if not found. No markdown formatting."""

def setup_database():
    conn = sqlite3.connect('finances.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            subject TEXT,
            snippet TEXT,
            ai_category TEXT,
            ai_justification TEXT,
            amount TEXT,
            user_status TEXT DEFAULT 'Pending Review',
            final_category TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    return conn

def get_gmail_service():
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('gmail', 'v1', credentials=creds)

def main():
    print("️  Setting up database...")
    db_conn = setup_database()
    cursor = db_conn.cursor()

    print(" Connecting to Gmail...")
    service = get_gmail_service()
    
    # Query for historical emails: Jan 1, 2026 to present
    today_str = datetime.now().strftime("%Y/%m/%d")
    query = f"(receipt OR invoice OR 'order confirmation' OR 'amazon order' OR from:amazon) after:2026/01/01 before:{today_str}"
    
    print(f" Searching Gmail with query: {query}")
    
    messages = []
    request = service.users().messages().list(userId='me', q=query)
    
    while request is not None:
        results = request.execute()
        messages.extend(results.get('messages', []))
        request = service.users().messages().list_next(previous_request=request, previous_response=results)

    if not messages:
        print("No receipts found.")
        return

    print(f" Found {len(messages)} historical receipts to process. This might take a while!")
    print("-" * 50)

    for i, message in enumerate(messages):
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        headers = msg['payload']['headers']
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), "No Date")
        if date_str != "No Date":
            try:
                parsed_tuple = email.utils.parsedate_tz(date_str)
                if parsed_tuple:
                    dt = datetime.fromtimestamp(email.utils.mktime_tz(parsed_tuple))
                    date = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    date = date_str[:16]
            except Exception:
                date = date_str[:16]
        else:
            date = "No Date"
            
        snippet = msg.get('snippet', 'No snippet available')
        
        print(f"\n[{i+1}/{len(messages)}] [{date[:16]}] {subject[:40]}...")
        
        # Check if already in DB to avoid duplicates on re-runs
        cursor.execute("SELECT id FROM receipts WHERE subject = ? AND date = ?", (subject, date))
        if cursor.fetchone():
            print("    Already in database, skipping...")
            continue

        print("    Asking Qwen to categorize...")

        try:
            completion = client.chat.completions.create(
                model="qwen3:8b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Subject: {subject}\nBody: {snippet}"}
                ],
                temperature=0.1
            )
            
            ai_response = completion.choices[0].message.content
            clean_json = ai_response.replace('```json', '').replace('```', '').strip()
            
            ai_data = json.loads(clean_json)
            category = ai_data.get('category', 'Error parsing')
            justification = ai_data.get('justification', 'Error parsing')
            amount = ai_data.get('amount', 'Unknown')
            
            print(f"   -> Result: {category} | Amount: {amount}")

            # Save to Database
            cursor.execute('''
                INSERT INTO receipts (date, subject, snippet, ai_category, ai_justification, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, subject, snippet, category, justification, amount))
            db_conn.commit()
            print("    Saved to finances.db")

        except Exception as e:
            print(f"    Failed to process: {e}")

    db_conn.close()
    print("\n Historical email pipeline complete!")

if __name__ == '__main__':
    main()
