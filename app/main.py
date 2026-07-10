from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.agent import get_current_agent, init_checkpointer
from app.routers import auth, chat, config, conversations, reports, settings, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await init_checkpointer()
    get_current_agent()
    print("[Vetlog] Agent ready.")
    yield


app = FastAPI(title="Vetlog AI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules
app.include_router(config.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(reports.router)
app.include_router(webhook.router)
app.include_router(settings.router)

@app.get("/")
def root():
    """Health-check endpoint."""
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
