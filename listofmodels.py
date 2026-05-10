# backend/list_models.py
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

print("--- AVAILABLE MULTIMODAL MODELS ---")
try:
    for m in client.models.list():
        # Look for models that support 'generateContent' (which includes Vision)
        if "generateContent" in m.supported_actions:
            print(f"ID: {m.name} | Display Name: {m.display_name}")
except Exception as e:
    print(f"Could not fetch models: {e}")