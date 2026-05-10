# api.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from main import process_invoice  # Make sure your logic is in main.py

app = FastAPI()

# Allow your local and Vercel URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For testing, we allow all. We can restrict later.
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Server is running"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # Save temp file
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    try:
        results = process_invoice(temp_path)
        os.remove(temp_path)
        return results
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)