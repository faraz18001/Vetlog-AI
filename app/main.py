from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import init_db, get_session, RawMessage
from app.schemas import RawMessageIn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"status": "alive"}


@app.post("/webhook/extension/")
def ingest_message(payload: RawMessageIn, db: Session = Depends(get_session)):
    msg = RawMessage(
        chat_name=payload.chat_name,
        sender=payload.sender,
        text=payload.text,
        timestamp=payload.timestamp,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    print(f"Ingested message #{msg.id}: [{payload.sender}] {payload.text[:60]}")
    return {"status": "received", "message_id": msg.id}
