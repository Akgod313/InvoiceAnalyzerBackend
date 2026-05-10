# backend/main.py
from google import genai
from google.genai import types
import PIL.Image
import json
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "master_database.csv")

if os.path.exists(db_path):
    with open(db_path, "r", encoding="utf-8") as file:
        database_content = file.read()
else:
    database_content = "No database found."
    print("WARNING: master_database.csv missing on server!")
# 1. Initialize Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. Use the stable model
MODEL_ID = "gemini-3-flash-preview" 

def clean_number(value):
    """Helper to safely turn strings or nulls into a clean float"""
    if value is None:
        return 0.0
    try:
        # Strip out currency symbols, commas, and letters
        clean_str = re.sub(r'[^\d.]', '', str(value))
        return float(clean_str) if clean_str else 0.0
    except:
        return 0.0

def process_invoice(image_path):
    try:
        img = PIL.Image.open(image_path)
        
        # Read the master database to give the AI context for matching
        db_path = "master_database.csv"
        database_content = ""
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as file:
                database_content = file.read()

        prompt = f"""
        Analyze this invoice image and extract details into a JSON object. 
        Look carefully for the Vendor Name, Invoice Number, Date, the type of Invoice and GSTIN number.
        
        NEW REQUIREMENTS:
        1. invoice_type: Identify if it is a 'Tax Invoice', 'Proforma', etc. (usually at the top).
        2. paid_to: Identify the name of the person/company the invoice is being paid to (usually follows 'To:').
        3. gstin_numbers: Extract ALL GSTIN numbers found on the document as a list.
        
        CRITICAL RULES FOR "items":
        - Extract ONLY physical products/materials. 
        - DO NOT extract "Subtotal", "Total", "CGST", "SGST", "IGST", "Round off", or "Grand Total" as items. 
        - Include "quantity" for each item.
        - Include "unit_price" (Calculate this by dividing the item amount by the quantity).

        CATEGORIZATION RULES:
        1. EXACT MATCH: If the item is in this database, use the exact Type and Sub_type listed:
        --- START DATABASE ---
        {database_content}
        --- END DATABASE ---
        
        2. NEW ITEMS: If it's not in the database, judge the category but use ONLY these strict pairings:
           - Boards: [Block Board, BWP, Flexi Ply, HDHMR, MDF, MR-PLY, PLPB]
           - Carpenter: [Carpenter Labour]
           - Civil Work(False Ceiling): [False Ceiling Material, FC Labour]
           - Cleaning: [Deep Cleaning, General Cleaning]
           - Hardware: [Consumables, Fixture, Frame, Handle, Hardware, Knobs, Pin Board]
           - Painting: [Duco Material, Duco Paint Material, Wall Paint Material, Wall Primer, Wall Putty]
           - EB: [Edge Bends], Electrical: [Electrical Materials], Lights: [Lights], Plumbing: [Plumbing Material]
           - Fabrication: [Laser Cutting, M S Plate], Floor Mats: [Floor Mats], Laminates: [Laminates, MM]
           - M&G: [Mirror, Fixed Glass Shower Partition, Sliding Glass Shower Partition, Swing Glass Shower partition]
           - Upholstery: [Curtains, Fabric], Transportation: [Transportation]
        
        You MUST return a JSON object that EXACTLY matches this structure:
        {{
            "vendor_name": "Name of Vendor",
            "invoice_no": "INV-123",
            "invoice_date": "DD-MM-YYYY",
            "invoice_total": 2600.00,
            "invoice_type": "e.g. Tax Invoice",
            "paid_to": "Name of receiver",
            "gstin_numbers": ["GSTIN1", "GSTIN2"],
            "items": [
                {{
                    "description": "Product Name",
                    "type": "Exact Type from list",
                    "sub_type": "Exact Sub-type from list",
                    "quantity": 2,
                    "unit_price": 500.00,
                    "amount": 1000.00,
                    "tax_percentage": 18
                }}
            ]
        }}
        """
        
        # Force strict JSON output
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        res_text = response.text.strip()
        print("\n--- RAW GEMINI OUTPUT ---")
        print(res_text)
        print("-------------------------\n")
        
        parsed_data = json.loads(res_text)
        
        # Extract Global Info
        vendor_name = parsed_data.get("vendor_name", "Unknown Vendor")
        inv_no = parsed_data.get("invoice_no", "N/A")
        inv_date = parsed_data.get("invoice_date", "N/A")
        invoice_total = clean_number(parsed_data.get("invoice_total", 0))
        raw_items = parsed_data.get("items", [])
        
        # Filter items to ensure no "Total" rows snuck in
        valid_items = []
        for item in raw_items:
            desc = item.get('description', 'Unknown')
            if any(word in desc.lower() for word in ['total', 'gst', 'subtotal', 'round off']):
                continue
            valid_items.append(item)
            
        is_single_item = (len(valid_items) == 1)
            
        final_report = []
        for item in valid_items:
            clean_item = {k.lower(): v for k, v in item.items()}
            desc = clean_item.get('description', 'Unknown')
            
            base_amount = clean_number(clean_item.get('amount', 0))
            tax_percentage = clean_number(clean_item.get('tax_percentage', 0))
            
            # Logic: If 1 item, use invoice total. If multiple, calculate individually.
            if is_single_item and invoice_total > 0:
                final_amount = invoice_total
            else:
                tax_amount = base_amount * (tax_percentage / 100)
                final_amount = base_amount + tax_amount
            
            final_report.append({
                "Vendor": vendor_name,
                "Invoice_No": inv_no,
                "Invoice_Date": inv_date,
                "Description": desc,
                "Type": clean_item.get('type', 'Uncategorized'),
                "Sub-type": clean_item.get('sub_type', 'N/A'),
                "Base_Amount": round(base_amount, 2),
                "Tax_Percent": round(tax_percentage, 1),
                "Final_Amount": round(final_amount, 2)
            })
        
        return final_report

    except Exception as e:
        print(f"--- EXTRACTION ERROR ---\n{str(e)}")
        raise e