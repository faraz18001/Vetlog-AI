from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.agent import initialize_agent
from app.config import INPUT_TOKEN_PRICE_PER_1K, OUTPUT_TOKEN_PRICE_PER_1K
from app.database import RawMessage, get_session, init_db
from app.schemas import (
    ChatRequest,
    ChatResponse,
    RawMessageBatchIn,
    RawMessageIn,
    TokenUsage,
    UsageStats,
)

app = FastAPI()

# Agent singleton — initialised once at startup so the
# MemorySaver checkpointer persists across requests.
_agent = None

# In-memory usage accumulator (resets on server restart).
_usage = {
    "total_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0,
}


def _extract_usage(messages: list) -> TokenUsage:
    """Sum usage_metadata across every AIMessage in a LangGraph turn."""
    inp = out = 0
    for msg in messages:
        meta = getattr(msg, "usage_metadata", None)
        if meta:
            inp += meta.get("input_tokens", 0)
            out += meta.get("output_tokens", 0)
    cost = (inp / 1000 * INPUT_TOKEN_PRICE_PER_1K) + (
        out / 1000 * OUTPUT_TOKEN_PRICE_PER_1K
    )
    return TokenUsage(
        input_tokens=inp,
        output_tokens=out,
        total_tokens=inp + out,
        cost_usd=round(cost, 6),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    global _agent
    init_db()
    _agent = initialize_agent()
    print("[Vetlog] Agent ready.")


@app.get("/")
def root():
    return {"status": "alive"}


@app.post("/chat/", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialised yet.")

    config = {"configurable": {"thread_id": payload.thread_id}}
    result = _agent.invoke(
        {"messages": [("user", payload.message)]},
        config=config,
    )

    messages = result["messages"]
    last = messages[-1]

    # content can be str or list[dict] on newer LangChain builds
    content = last.content
    if not isinstance(content, str):
        content = " ".join(
            part if isinstance(part, str) else part.get("text", "") for part in content
        )

    usage = _extract_usage(messages)

    # Accumulate session stats
    _usage["total_requests"] += 1
    _usage["total_input_tokens"] += usage.input_tokens
    _usage["total_output_tokens"] += usage.output_tokens
    _usage["total_tokens"] += usage.total_tokens
    _usage["total_cost_usd"] += usage.cost_usd

    print(
        f"[usage] req #{_usage['total_requests']} "
        f"in={usage.input_tokens} out={usage.output_tokens} "
        f"cost=${usage.cost_usd:.6f} | "
        f"session total=${_usage['total_cost_usd']:.4f}"
    )

    return ChatResponse(response=content, thread_id=payload.thread_id, usage=usage)


@app.get("/usage/", response_model=UsageStats)
def usage_stats():
    """Cumulative token + cost stats since last server start."""
    return UsageStats(
        **_usage,
        pricing_configured=(
            INPUT_TOKEN_PRICE_PER_1K > 0 or OUTPUT_TOKEN_PRICE_PER_1K > 0
        ),
    )


@app.post("/webhook/extension/")
def ingest_message(payload: RawMessageIn, db: Session = Depends(get_session)):
    # Check if this message already exists
    exists = (
        db.query(RawMessage)
        .filter(
            RawMessage.chat_name == payload.chat_name,
            RawMessage.sender == payload.sender,
            RawMessage.text == payload.text,
            RawMessage.timestamp == payload.timestamp,
        )
        .first()
    )

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
    existing_messages = (
        db.query(RawMessage).filter(RawMessage.chat_name.in_(chat_names)).all()
    )

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
