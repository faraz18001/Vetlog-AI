from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_session, RawMessage
from app.schemas import RawMessageBatchIn

router = APIRouter(prefix="/webhook/extension", tags=["webhook"])

@router.post("/batch/")
def ingest_batch(payload: RawMessageBatchIn, db: Session = Depends(get_session)):
    """
    Receive a batch of WhatsApp messages from the Chrome extension.
    Deduplication is done safely in memory.
    """
    if not payload.messages:
        return {"status": "received", "count": 0}

    try:
        # Collect the unique chat names present in this batch.
        chat_names = {msg.chat_name for msg in payload.messages}

        # Query ONLY the three specific columns we need for the signature.
        # This prevents loading massive ORM objects into RAM.
        existing_records = db.query(
            RawMessage.sender, 
            RawMessage.text, 
            RawMessage.timestamp
        ).filter(RawMessage.chat_name.in_(chat_names)).all()

        # existing_records will just be a list of tuples like: ("You", "Hello", "5:21 pm...")
        seen_signatures = set(existing_records)

        new_messages = []
        for msg_data in payload.messages:
            signature = (msg_data.sender, msg_data.text, msg_data.timestamp)

            if signature in seen_signatures:
                continue

            # Append to a list instead of adding to DB one by one
            new_messages.append(
                RawMessage(
                    chat_name=msg_data.chat_name,
                    sender=msg_data.sender,
                    text=msg_data.text,
                    timestamp=msg_data.timestamp,
                )
            )
            # Track locally to catch duplicates within the incoming batch itself
            seen_signatures.add(signature)

        # Efficiency : Add all at once, then commit
        if new_messages:
            db.add_all(new_messages)
            db.commit()

        print(f"Ingested batch: {len(new_messages)} new messages (duplicates skipped)")
        return {"status": "received", "count": len(new_messages)}

    except Exception as e:
        # If literally anything fails, rollback the session so SQLite doesn't get locked!
        db.rollback()
        print(f"CRITICAL: Database error during batch ingestion: {e}")
        raise HTTPException(status_code=500, detail="Database insertion failed.")