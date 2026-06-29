# Vetlog AI

Veterinary clinic AI assistant. Queries clinic WhatsApp data via natural language.

---

## Setup

### 1. Backend

```bash
# Create virtual environment (first time only)
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env` to the project root (we'll share this privately). It contains which AI provider/model to use and the API key.

### 3. Database

The SQLite database lives at `data/vetlog.db`. If it's empty, the WhatsApp Chrome extension populates it.

---

## Running

Open **two terminals**:

### Terminal 1 — Backend (FastAPI)

```bash
source .venv/bin/activate
python -m app.main
```

Backend runs at `http://localhost:8000`

### Terminal 2 — Frontend (React + Vite)

```bash
cd frontend
npm install    # first time only
npm run dev
```

Frontend runs at `http://localhost:5173`

Open `http://localhost:5173` in your browser.

---

## Backend Routes (for reference)

| Route | Purpose |
|---|---|
| `/` | Health check |
| `/chat/` | Send a message (POST) |
| `/chat/stream/` | Send a message, stream response (SSE) |
| `/usage/` | Token/cost stats |
| `/api/config/llm` | Get/set AI provider (GET/POST) |
| `/reports/{filename}` | View or export a report |
| `/webhook/extension/batch/` | Ingest WhatsApp messages from the Chrome extension |

---

## Chrome Extension

The `whatsapp_extension/` folder is a Chrome extension that scrapes WhatsApp Web messages. To install:
1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select `whatsapp_extension/`
4. Open `https://web.whatsapp.com`, pin the extension, and scrape

---

## Testing

```bash
source .venv/bin/activate
deepeval test run tests/test_agent.py -v
```

---

## Tech Stack

- **Backend:** Python, FastAPI, LangGraph, SQLAlchemy, SQLite
- **Frontend:** React 18, Vite, Framer Motion, React Markdown
- **LLM providers:** Ollama, Gemini, Groq, Mistral, Cerebras, OpenRouter, OpenAI
