from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import ConversationLog, get_session
from app.schemas import ConversationThread, ConversationMessage

router = APIRouter(prefix="", tags=["conversations"])


@router.get("/conversations/")
def list_conversations(
    user_id: int = Query(...),
    db: Session = Depends(get_session),
):
    subquery = (
        db.query(
            ConversationLog.thread_id,
            func.max(ConversationLog.created_at).label("latest_at"),
        )
        .filter(ConversationLog.user_id == user_id)
        .group_by(ConversationLog.thread_id)
        .subquery()
    )

    threads = (
        db.query(ConversationLog)
        .join(
            subquery,
            (ConversationLog.thread_id == subquery.c.thread_id)
            & (ConversationLog.created_at == subquery.c.latest_at),
        )
        .order_by(desc(subquery.c.latest_at))
        .all()
    )

    result = []
    for t in threads:
        result.append(
            ConversationThread(
                thread_id=t.thread_id,
                thread_name=t.thread_name,
                updated_at=t.created_at,
            )
        )

    return result


@router.get("/conversations/{thread_id}")
def get_conversation(
    thread_id: str,
    user_id: int = Query(...),
    db: Session = Depends(get_session),
):
    logs = (
        db.query(ConversationLog)
        .filter(
            ConversationLog.thread_id == thread_id,
            ConversationLog.user_id == user_id,
        )
        .order_by(ConversationLog.turn_number)
        .all()
    )

    result = []
    for log in logs:
        result.append(
            ConversationMessage(
                role=log.role,
                content=log.content,
                thread_name=log.thread_name,
                created_at=log.created_at,
            )
        )

    return result
