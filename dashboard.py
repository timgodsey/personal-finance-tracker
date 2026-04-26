from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import uvicorn

app = FastAPI()

# Data model for the web form submission
class ReceiptUpdate(BaseModel):
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

# 2. Feed the UI the pending data
@app.get("/api/pending")
def get_pending_receipts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipts WHERE user_status = 'Pending Review' ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# 3. Handle the approval clicks
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

if __name__ == "__main__":
    print("🚀 Godsey Fabrications Finance Server running at: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)