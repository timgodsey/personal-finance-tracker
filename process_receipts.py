import os
import json
import sqlite3
import email.utils
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI

# --- CONFIGURATION ---
# Point to Open WebUI and authenticate with your specific JWT
client = OpenAI(
    base_url="http://100.119.170.3:3000/api", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjljYWE1ZDhjLWEzYTMtNGQxMy04MjIyLTk0YTZiMzBmMDk4OSIsImV4cCI6MTc3OTM0MzI3MSwianRpIjoiNTA2N2RjYjMtNjEwMy00NmI0LWFmYTYtNjZhYTg4MWE3YTk2In0.Y6cDvIfNX8du6Fdmylbjwg2gBcQMQkTBFnfzqpFhjMg"
)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

system_prompt = """You are an expert financial categorizer. I run a fabrication, 3D printing, and electronics business called Godsey Fabrications. 
Analyze the following receipt text and categorize it.
Buckets: 'Definitely Business', 'Maybe Business', 'Definitely Personal'.
Output ONLY valid JSON with keys: "category", "justification", and "amount". Extract the total transaction amount (e.g. "$124.50") for the "amount" field, or "Unknown" if not found. No markdown formatting."""

def setup_database():
    """Creates the SQLite database and the updated receipts table."""
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
    """Authenticates and returns the Gmail service."""
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('gmail', 'v1', credentials=creds)

def main():
    print("🗄️  Setting up database...")
    db_conn = setup_database()
    cursor = db_conn.cursor()

    print("📧 Connecting to Gmail...")
    service = get_gmail_service()
    
    # Grab the 5 most recent receipts for processing
    query = "receipt OR invoice OR 'order confirmation' OR 'amazon order' OR from:amazon"
    results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No receipts found.")
        return

    for message in messages:
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
        
        print(f"\n[{date[:16]}] {subject[:40]}...")
        print("🧠 Asking Qwen to categorize...")

        try:
            # Send to local Open WebUI instance, strictly targeting Qwen
            completion = client.chat.completions.create(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Subject: {subject}\nBody: {snippet}"}
                ],
                temperature=0.1
            )
            
            # Parse the AI's JSON response
            ai_response = completion.choices[0].message.content
            # Strip markdown code blocks just in case the AI hallucinates them
            clean_json = ai_response.replace('```json', '').replace('```', '').strip()
            
            ai_data = json.loads(clean_json)
            category = ai_data.get('category', 'Error parsing')
            justification = ai_data.get('justification', 'Error parsing')
            amount = ai_data.get('amount', 'Unknown')
            
            print(f"   ↳ Result: {category} | Amount: {amount} | {justification[:50]}...")

            # Save to Database
            cursor.execute('''
                INSERT INTO receipts (date, subject, snippet, ai_category, ai_justification, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, subject, snippet, category, justification, amount))
            db_conn.commit()
            print("   💾 Saved to finances.db")

        except Exception as e:
            print(f"   ❌ Failed to process: {e}")

    db_conn.close()
    print("\n✅ Pipeline complete!")

if __name__ == '__main__':
    main()