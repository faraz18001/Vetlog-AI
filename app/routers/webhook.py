from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_session, RawMessage
from app.schemas import RawMessageBatchIn
from datetime import datetime

def parse_whatsapp_timestamp(ts: str) -> str:
    """
    Converts WhatsApp timestamp to ISO-8601 format before storing.
    Input:  '5:49 pm, 30/06/2026'
    Output: '2026-06-30 17:49:00'
    """
    try:
        dt = datetime.strptime(ts.strip(), "%I:%M %p, %d/%m/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts

router = APIRouter(prefix="/webhook/extension", tags=["webhook"])

@router.post("/batch/")
def ingest_batch(payload: RawMessageBatchIn, db: Session = Depends(get_session)):
    if not payload.messages:
        return {"status": "received", "count": 0}

    try:
        chat_names = {msg.chat_name for msg in payload.messages}

        existing_records = db.query(
            RawMessage.sender, 
            RawMessage.text, 
            RawMessage.timestamp
        ).filter(RawMessage.chat_name.in_(chat_names)).all()

        seen_signatures = set(existing_records)

        new_messages = []
        for msg_data in payload.messages:
            parsed_ts = parse_whatsapp_timestamp(msg_data.timestamp)
            signature = (msg_data.sender, msg_data.text, parsed_ts)

            if signature in seen_signatures:
                continue

            new_messages.append(
                RawMessage(
                    chat_name=msg_data.chat_name,
                    sender=msg_data.sender,
                    text=msg_data.text,
                    timestamp=parsed_ts,
                )
            )
            seen_signatures.add(signature)

        if new_messages:
            db.add_all(new_messages)
            db.commit()

        print(f"Ingested batch: {len(new_messages)} new messages (duplicates skipped)")
        return {"status": "received", "count": len(new_messages)}

    except Exception as e:
        db.rollback()
        print(f"CRITICAL: Database error during batch ingestion: {e}")
        raise HTTPException(status_code=500, detail="Database insertion failed.")