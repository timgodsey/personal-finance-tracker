from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import uvicorn
import subprocess
import os

app = FastAPI()

# Data models
class ReceiptUpdate(BaseModel):
    id: int
    final_category: str
    notes: str

class TransactionUpdate(BaseModel):
    id: int
    final_category: str
    notes: str

def get_db_connection():
    conn = sqlite3.connect('finances.db')
    conn.row_factory = sqlite3.Row 
    return conn

# 1. Serve the UI
@app.get("/")
def serve_dashboard():
    return FileResponse("index.html")

# 2. Feed the UI the pending receipts
@app.get("/api/pending")
def get_pending_receipts():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if table exists (in case audit hasn't run yet)
    try:
        cursor.execute("SELECT * FROM receipts WHERE user_status = 'Pending Review' ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

# 3. Feed the UI the pending bank transactions with auto-matching
@app.get("/api/pending_transactions")
def get_pending_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM transactions WHERE user_status = 'Pending Review' ORDER BY date DESC")
        tx_rows = cursor.fetchall()
        
        transactions = []
        for tx in tx_rows:
            tx_dict = dict(tx)
            tx_amount = tx_dict.get('amount', '')
            
            # Auto-matching logic
            matched_receipt = None
            if tx_amount and tx_amount != 'Unknown':
                try:
                    # Strip symbols and convert to float
                    clean_tx_amount = float(str(tx_amount).replace('$', '').replace(',', ''))
                    
                    # Look for receipts with matching amounts
                    cursor.execute("SELECT * FROM receipts WHERE amount IS NOT NULL AND amount != 'Unknown'")
                    all_receipts = cursor.fetchall()
                    
                    for r in all_receipts:
                        r_amount_str = str(r['amount']).replace('$', '').replace(',', '')
                        try:
                            if abs(float(r_amount_str) - clean_tx_amount) < 0.01:
                                # Simple match based on amount (could also check date proximity)
                                matched_receipt = dict(r)
                                break
                        except ValueError:
                            continue
                            
                except ValueError:
                    pass
            
            tx_dict['matched_receipt'] = matched_receipt
            transactions.append(tx_dict)
            
        return transactions
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

# 4. Handle receipt approval clicks
@app.post("/api/approve")
def approve_receipt(update: ReceiptUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE receipts 
        SET user_status = 'Approved', final_category = ?, notes = ?
        WHERE id = ?
    ''', (update.final_category, update.notes, update.id))
    conn.commit()
    conn.close()
    return {"status": "success"}

# 5. Handle transaction approval clicks
@app.post("/api/approve_transaction")
def approve_transaction(update: TransactionUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transactions 
        SET user_status = 'Approved', final_category = ?, notes = ?
        WHERE id = ?
    ''', (update.final_category, update.notes, update.id))
    conn.commit()
    conn.close()
    return {"status": "success"}

# 6. One-time audit endpoint
def run_audit_scripts():
    print("Starting One-Time Audit...")
    try:
        print("   Running Email Audit...")
        subprocess.run(["python", "pull_historical_emails.py"], check=True)
        print("   Running Plaid Audit...")
        subprocess.run(["python", "pull_historical_plaid.py"], check=True)
        print(" Audit complete!")
    except Exception as e:
        print(f" Audit failed: {e}")

@app.post("/api/audit")
def trigger_audit(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_audit_scripts)
    return {"status": "Audit started in background. Check terminal for progress."}

if __name__ == "__main__":
    print("Godsey Fabrications Finance Server running at: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)