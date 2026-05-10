import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil

# --- CRITICAL: IMPORT YOUR LOGIC ---
# This assumes your extraction logic is in a file named main.py
try:
    from main import process_invoice
except ImportError:
    # Fallback if you renamed your logic file
    def process_invoice(path):
        return {"error": "process_invoice function not found in main.py"}

app = FastAPI()

# --- CORS SETTINGS ---
# This allows your local React app and your future Vercel app to talk to Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For initial deployment, allow all. Restrict later for security.
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HEALTH CHECK ROUTE ---
# Visit your-render-url.onrender.com/ in a browser to see if the server is up
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Quotation Extractor API is running",
        "database_connected": os.environ.get("DATABASE_URL") is not None
    }

# --- MAIN ANALYSIS ROUTE ---
@app.post("/analyze")
async def analyze_invoice(file: UploadFile = File(...)):
    # 1. Create a temporary file path
    temp_file_path = f"temp_{file.filename}"
    
    try:
        # 2. Save the uploaded image locally so Gemini can read it
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 3. Run your extraction logic from main.py
        results = process_invoice(temp_file_path)
        
        # 4. Return the results to the React frontend
        return results

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 5. Clean up: Delete the temporary image file after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# --- RENDER STARTUP LOGIC ---
if __name__ == "__main__":
    # Render provides a 'PORT' environment variable. If not found, use 10000.
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)