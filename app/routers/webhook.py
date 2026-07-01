from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_session, RawMessage
from app.schemas import RawMessageBatchIn


def _parse_timestamp(ts: str) -> str:
    """
    Convert a WhatsApp-format timestamp to ISO-8601 before storing.

    Auto-detects locale format so it works regardless of whether
    WhatsApp was set to US (MM/DD/YYYY) or DD/MM/YYYY.

    Migration dependency: run data/migrate_timestamps.py FIRST so
    existing rows are converted to ISO. Then this parser keeps new
    ingests consistent.
    """
    ts = ts.strip()

    # Already ISO — leave untouched
    if ts.startswith("202"):
        return ts

    # US format: "9:03 PM, 3/27/2026"
    try:
        dt = datetime.strptime(ts, "%I:%M %p, %m/%d/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    # DD/MM/YYYY format: "5:49 pm, 30/06/2026"
    try:
        dt = datetime.strptime(ts, "%I:%M %p, %d/%m/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    return ts  # Unrecognised — store as-is

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
        # Normalise timestamp to ISO so it matches stored format after migration
        normalized_ts = _parse_timestamp(msg_data.timestamp)
        signature = (msg_data.sender, msg_data.text, normalized_ts)

        if signature in seen_signatures:
            continue

        new_message = RawMessage(
            chat_name=msg_data.chat_name,
            sender=msg_data.sender,
            text=msg_data.text,
            timestamp=normalized_ts,
        )
        db.add(new_message)

        # Track it locally so duplicates within the same batch are also caught.
        seen_signatures.add(signature)
        inserted_count += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Webhook: Database commit failed, rolled back: {e}")
        raise HTTPException(status_code=500, detail="Database insertion failed.")

    print(f"Ingested batch: {inserted_count} new messages (duplicates skipped)")
    return {"status": "received", "count": inserted_count}
