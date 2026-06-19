import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///vetlog.db")
"""Mr Ammar And Slime Nigga Please Use your Own API-Key"""
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3")
