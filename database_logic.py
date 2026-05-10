# backend/database_logic.py
import pandas as pd
from thefuzz import process
from config import DATABASE_PATH

# Load the database into memory
df_master = pd.read_csv(DATABASE_PATH)

def get_material_details(extracted_name):
    # Extract the best match and its index
    match, score, match_index = process.extractOne(extracted_name, df_master['Item_Keyword'])
    
    if score > 70:
        row = df_master.iloc[match_index]
        
        # 1. Grab the Type (Default to Uncategorized if somehow missing)
        item_type = str(row['Type']).strip() if pd.notna(row['Type']) else "Uncategorized"
        
        # 2. Grab the Sub-type raw value
        raw_sub_type = row['Sub_type']
        
        # 3. THE NEW RULE: Check if it's missing (NaN) or just a blank string
        if pd.isna(raw_sub_type) or str(raw_sub_type).strip() == "":
            final_sub_type = item_type  # Fill with the Type
        else:
            final_sub_type = str(raw_sub_type).strip()
            
        return {
            "Type": item_type,
            "Sub_type": final_sub_type, # Standardized key for main.py
            "Match_Score": score
        }
        
    # If no match is found, fill both with "New/Unknown"
    return {"Type": "New/Unknown", "Sub_type": "New/Unknown", "Match_Score": score}