"""
VyaparSathi Configuration
======================
Loads environment variables and defines application-wide settings.
All secrets (API keys) are loaded from a .env file and never hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# â”€â”€ AI Provider â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Supports "groq" (default, free) or "gemini"
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "groq")

# â”€â”€ Groq API (FREE â€” default) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# â”€â”€ Gemini API (backup) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# â”€â”€ Server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# â”€â”€ Agent Tuning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MAX_SEARCH_QUERIES: int = int(os.getenv("MAX_SEARCH_QUERIES", "5"))
MAX_COMPETITORS: int = int(os.getenv("MAX_COMPETITORS", "8"))
MAX_SCRAPE_PAGES: int = int(os.getenv("MAX_SCRAPE_PAGES", "5"))

