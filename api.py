# backend/api.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os

# Import your existing logic
from main import process_invoice 

app = FastAPI()

# CRITICAL: This allows your Vite app (running on a different port) 
# to talk to your Python server without being blocked.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    # Create the uploads folder if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    
    # Save the file locally so Gemini can read it
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Run your AI + Database logic
        results = process_invoice(file_path)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)