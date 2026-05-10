import os
import json
import psycopg2
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
from main import process_invoice

app = FastAPI()

# Allow your Vercel frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fetch the database URL from Render environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

def save_to_database(data):
    # If there is an error in extraction, don't save it
    if "error" in data or not DATABASE_URL:
        return False

    try:
        # Connect to Neon
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Join the GSTIN array into a single comma-separated string
        gstin_str = ", ".join(data.get("gstin_numbers", [])) if data.get("gstin_numbers") else "N/A"

        # Convert the items list into a JSON string for the JSONB column
        items_json = json.dumps(data.get("items", []))

        # Insert query
        insert_query = """
            INSERT INTO invoices 
            (vendor_name, vendor_address, invoice_no, invoice_date, invoice_type, paid_to, gstin_numbers, items)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            data.get("vendor_name"),
            data.get("vendor_address"),
            data.get("invoice_no"),
            data.get("invoice_date"),
            data.get("invoice_type"),
            data.get("paid_to"),
            gstin_str,
            items_json
        ))

        # Commit and close
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Successfully saved to Neon Database!")
        return True

    except Exception as e:
        print("❌ Database Error:", str(e))
        return False

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Read your database logic for categorization
    db_content = ""
    if os.path.exists("master_database.csv"):
        with open("master_database.csv", "r") as f:
            db_content = f.read()

    # 2. Extract data using Gemini (from main.py)
    results = process_invoice(temp_path, database_content=db_content)
    
    # 3. Save to Neon Database
    save_to_database(results)

    # 4. Clean up the temp image
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # 5. Send results back to React frontend
    return results