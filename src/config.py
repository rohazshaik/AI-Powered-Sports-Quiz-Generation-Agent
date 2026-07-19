import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not gemini_api_key:
    print("[WARNING] GEMINI_API_KEY is missing. Add it to your .env file.")
chroma_db_path = "./chroma_db"
collection_name = "sports_history"
