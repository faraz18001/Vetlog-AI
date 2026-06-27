from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_session, RawMessage
from app.schemas import RawMessageBatchIn

router = APIRouter(prefix="/webhook/extension", tags=["webhook"])

@router.post("/batch/")
def ingest_batch(payload: RawMessageBatchIn, db: Session = Depends(get_session)):
    """
    Receive a batch of WhatsApp messages from the Chrome extension.
    Deduplication is done in memory rather than with one DB query per message.
    """
    if not payload.messages:
        return {"status": "received", "count": 0}

    # Collect the unique chat names present in this batch.
    chat_names = set()
    for msg in payload.messages:
        chat_names.add(msg.chat_name)

    # Load all existing messages for those chats in one query.
    existing = db.query(RawMessage).filter(RawMessage.chat_name.in_(chat_names)).all()

    # A signature is (sender, text, timestamp) — enough to detect duplicates.
    seen_signatures = set()
    for msg in existing:
        signature = (msg.sender, msg.text, msg.timestamp)
        seen_signatures.add(signature)

    inserted_count = 0
    for msg_data in payload.messages:
        signature = (msg_data.sender, msg_data.text, msg_data.timestamp)

        if signature in seen_signatures:
            continue

        new_message = RawMessage(
            chat_name=msg_data.chat_name,
            sender=msg_data.sender,
            text=msg_data.text,
            timestamp=msg_data.timestamp,
        )
        db.add(new_message)

        # Track it locally so duplicates within the same batch are also caught.
        seen_signatures.add(signature)
        inserted_count += 1

    db.commit()
    print(f"Ingested batch: {inserted_count} new messages (duplicates skipped)")
    return {"status": "received", "count": inserted_count}
