# api.py
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import your extraction logic from main.py
try:
    from main import process_invoice
except ImportError:
    # This prevents the whole server from crashing if main.py has an issue
    def process_invoice(path):
        return {"error": "Main logic file (main.py) or process_invoice function not found."}

app = FastAPI()

# --- CORS SETTINGS ---
# This allows your separate Vercel frontend to talk to this Render backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all domains. Best for testing; you can restrict to your Vercel URL later.
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- HEALTH CHECK ---
# If you visit your-url.onrender.com/ in a browser, you should see this JSON.
@app.get("/")
def home():
    return {
        "status": "online", 
        "message": "Quotation API is active",
        "database_configured": "DATABASE_URL" in os.environ
    }

# --- ANALYSIS ROUTE ---
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # Create a unique temporary filename
    temp_path = f"temp_{file.filename}"
    
    try:
        # Save the uploaded file from the frontend to the server temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run the Gemini extraction logic
        results = process_invoice(temp_path)
        
        return results

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Always delete the temp file so the server doesn't get cluttered
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- STARTUP LOGIC ---
if __name__ == "__main__":
    # Render automatically sets a 'PORT' environment variable
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)