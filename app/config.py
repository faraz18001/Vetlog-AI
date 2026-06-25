import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/vetlog.db")
"""Mr Ammar And Slime Nigga Please Use your Own API-Key"""
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3")

# Token pricing — fill these from your Ollama Cloud dashboard.
# Price is USD per 1 000 tokens. Leave as 0 if unknown; counts still show.
INPUT_TOKEN_PRICE_PER_1K = float(os.environ.get("INPUT_TOKEN_PRICE_PER_1K", "0"))
OUTPUT_TOKEN_PRICE_PER_1K = float(os.environ.get("OUTPUT_TOKEN_PRICE_PER_1K", "0"))
