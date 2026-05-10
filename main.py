import os
import json
from google import genai
from PIL import Image

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def process_invoice(image_path, database_content=""):
    img = Image.open(image_path)

    # UPDATED PROMPT: Added vendor_address to the required JSON structure
    prompt = f"""
        Analyze this invoice image and extract details into a JSON object. 
        Look carefully for the Vendor Name, Vendor Address, Invoice Number, Date, the type of Invoice and GSTIN number.
        
        CRITICAL RULES FOR "items":
        - Extract ONLY physical products/materials. 
        - DO NOT extract "Subtotal", "Total", "CGST", "SGST", "IGST", "Round off", or "Grand Total" as items. 
        
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
            "vendor_name": "Name of the shop/vendor issuing the invoice",
            "vendor_address": "The full physical address of the vendor/shop(usually there is Bangalore in that sentence)",
            "invoice_no": "INV-123",
            "invoice_date": "DD-MM-YYYY",
            "invoice_total": 2600.00,
            "invoice_type": "Extract Type (Tax Invoice, etc.)",
            "paid_to": "The exact name written after 'To:', 'M/s', or 'Billed To' (The customer receiving the goods)",
            "gstin_numbers": ["Number 1", "Number 2"],
            "items": [
                {{
                    "description": "Product Name",
                    "hsn_sac": "Extract HSN or SAC code (if present)", 
                    "type": "Exact Type from list",
                    "sub_type": "Exact Sub-type from list",
                    "quantity": 1,
                    "unit_price": 0.00,
                    "amount": 1000.00,
                    "tax_percentage": 18
                }}
            ]
            ]
        }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[prompt, img]
        )

        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        data = json.loads(text.strip())

        if isinstance(data, list):
            data = data[0]

        if "items" not in data:
            data["items"] = []
            
        for item in data.get("items", []):
            qty = float(item.get("quantity", 1))
            amt = float(item.get("amount", 0))
            if "unit_price" not in item or item["unit_price"] == 0:
                item["unit_price"] = round(amt / qty, 2) if qty > 0 else amt

        return data

    except Exception as e:
        print(f"Extraction Error: {e}")
        return {"error": str(e), "items": []}