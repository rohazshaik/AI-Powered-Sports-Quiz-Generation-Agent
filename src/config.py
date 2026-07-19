"""
Loads secrets and shared settings so the rest of the app never
touches os.environ directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[1]
load_dotenv(project_root / ".env")

gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not gemini_api_key:
    print("[WARNING] GEMINI_API_KEY is missing. Add it to your .env file.")

# Where the vector database files live on disk
chroma_db_path = "./chroma_db"

# Name of the ChromaDB collection that stores our offline sports facts
collection_name = "sports_history"
