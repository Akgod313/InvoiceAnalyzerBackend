import os
import json
import psycopg2
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import shutil
from main import process_invoice

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")

def save_to_database(data):
    if "error" in data:
        print("❌ Skipping DB save due to extraction error.")
        return "Skipped: Extraction Error"

    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set in Render!")
        return "Error: Missing DATABASE_URL in Render"

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        gstin_str = ", ".join(data.get("gstin_numbers", [])) if data.get("gstin_numbers") else "N/A"
        
        insert_query = """
            INSERT INTO invoices 
            (vendor_name, vendor_address, invoice_no, invoice_date, invoice_type, paid_to, gstin_numbers,
             description, hsn_sac, type, sub_type, tax_percentage, quantity, unit_price, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        items = data.get("items", [])
        
        if items:
            flat_data = [
                (
                    data.get("vendor_name"),
                    data.get("vendor_address"),
                    data.get("invoice_no"),
                    data.get("invoice_date"),
                    data.get("invoice_type"),
                    data.get("paid_to"),
                    gstin_str,
                    item.get("description"),
                    item.get("hsn_sac"),
                    item.get("type"),
                    item.get("sub_type"),
                    item.get("tax_percentage"),
                    item.get("quantity"),
                    item.get("unit_price"),
                    item.get("amount")
                )
                for item in items
            ]
            cursor.executemany(insert_query, flat_data)
        else:
            # Fallback for 0 items
            cursor.execute(insert_query, (
                data.get("vendor_name"), data.get("vendor_address"), data.get("invoice_no"), 
                data.get("invoice_date"), data.get("invoice_type"), data.get("paid_to"), gstin_str,
                None, None, None, None, None, None, None, None
            ))

        conn.commit()
        cursor.close()
        conn.close()
        return "Success"

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Database Error: {error_msg}")
        if 'conn' in locals():
            conn.rollback() 
        return f"DB Error: {error_msg}"


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_content = ""
    if os.path.exists("master_database.csv"):
        with open("master_database.csv", "r") as f:
            db_content = f.read()

    # Extract data using Gemini
    results = process_invoice(temp_path, database_content=db_content)
    
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # 🚨 THIS WAS THE MISSING LINE! It sends the data back to React.
    return results


@app.post("/save")
async def save_invoice(request: Request):
    # This catches the edited data directly from your React frontend Upload button
    data = await request.json()
    status = save_to_database(data)
    return {"status": status}