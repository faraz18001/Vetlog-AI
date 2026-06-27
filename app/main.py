from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.agent import get_current_agent
from app.routers import chat, config, reports, webhook

app = FastAPI(title="Vetlog AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules
app.include_router(config.router)
app.include_router(chat.router)
app.include_router(reports.router)
app.include_router(webhook.router)


@app.on_event("startup")
def startup():
    """Initialise the database and the LangGraph agent on server start."""
    init_db()
    # Initialize the singleton agent here so it's ready before the first request
    get_current_agent()
    print("[Vetlog] Agent ready.")


@app.get("/")
def root():
    """Health-check endpoint."""
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
