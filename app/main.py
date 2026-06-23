from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import init_db, get_session, RawMessage
from app.schemas import RawMessageIn, RawMessageBatchIn

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
    # Check if this message already exists
    exists = db.query(RawMessage).filter(
        RawMessage.chat_name == payload.chat_name,
        RawMessage.sender == payload.sender,
        RawMessage.text == payload.text,
        RawMessage.timestamp == payload.timestamp
    ).first()
    
    if exists:
        return {"status": "already_exists", "message_id": exists.id}

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


@app.post("/webhook/extension/batch/")
def ingest_batch(payload: RawMessageBatchIn, db: Session = Depends(get_session)):
    if not payload.messages:
        return {"status": "received", "count": 0}

    # Retrieve all unique chat names from the payload
    chat_names = list(set(msg.chat_name for msg in payload.messages))
    
    # Query all existing messages for these chats to do in-memory deduplication
    existing_messages = db.query(RawMessage).filter(
        RawMessage.chat_name.in_(chat_names)
    ).all()
    
    # Build a set of signatures (sender, text, timestamp) for O(1) matching
    existing_signatures = {
        (msg.sender, msg.text, msg.timestamp) for msg in existing_messages
    }
    
    count = 0
    for msg_data in payload.messages:
        sig = (msg_data.sender, msg_data.text, msg_data.timestamp)
        if sig not in existing_signatures:
            msg = RawMessage(
                chat_name=msg_data.chat_name,
                sender=msg_data.sender,
                text=msg_data.text,
                timestamp=msg_data.timestamp,
            )
            db.add(msg)
            # Add new signature to set in case of duplicates within the same batch payload
            existing_signatures.add(sig)
            count += 1

    db.commit()
    print(f"Ingested batch: {count} messages (skipped duplicates)")
    return {"status": "received", "count": count}
