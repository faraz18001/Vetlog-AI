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

# In-memory usage accumulator — resets on server restart.
_usage = {
    "total_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0,
}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialise the database and the LangGraph agent on server start."""
    global _agent
    init_db()
    _agent = initialize_agent()
    print("[Vetlog] Agent ready.")


@app.get("/")
def root():
    """Health-check endpoint."""
    return {"status": "alive"}


def extract_content(message) -> str:
    """
    Pull the text content out of a LangChain message.

    Older LangChain versions return content as a plain string.
    Newer versions may return a list of content blocks like:
        [{"type": "text", "text": "Hello"}, ...]
    This function handles both shapes and always returns a plain string.
    """
    content = message.content

    if isinstance(content, str):
        return content

    # Content is a list of blocks — extract the text from each one.
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        else:
            parts.append(block.get("text", ""))

    return " ".join(parts)


def extract_usage(messages: list) -> TokenUsage:
    """
    Calculate token usage and estimated cost for a LangGraph agent turn.

    LangGraph may produce several AI messages in one turn (e.g. one for
    the tool call reasoning and one for the final answer). This function
    sums usage_metadata across all of them so the total reflects the full
    cost of answering one user question.

    Args:
        messages: The full message list returned by agent.invoke().

    Returns:
        A TokenUsage object with input/output token counts and cost in USD.
    """
    total_input = 0
    total_output = 0

    for message in messages:
        metadata = getattr(message, "usage_metadata", None)
        if metadata is None:
            continue
        total_input += metadata.get("input_tokens", 0)
        total_output += metadata.get("output_tokens", 0)

    input_cost = (total_input / 1000) * INPUT_TOKEN_PRICE_PER_1K
    output_cost = (total_output / 1000) * OUTPUT_TOKEN_PRICE_PER_1K
    total_cost = round(input_cost + output_cost, 6)

    return TokenUsage(
        input_tokens=total_input,
        output_tokens=total_output,
        total_tokens=total_input + total_output,
        cost_usd=total_cost,
    )


def accumulate_usage(usage: TokenUsage):
    """
    Add the usage from one request into the in-memory session totals.

    Args:
        usage: The TokenUsage object returned by extract_usage().
    """
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


@app.post("/chat/", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """
    Send a message to the Vetlog AI agent and get a response.

    The agent queries the SQLite database using natural language and
    returns an answer. Token usage is tracked per request.

    Args:
        payload: Contains the user's message and a thread_id for
                 conversation memory.

    Returns:
        The agent's response text along with token usage data.
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialised yet.")

    config = {"configurable": {"thread_id": payload.thread_id}}

    result = _agent.invoke(
        {"messages": [("user", payload.message)]},
        config=config,
    )

    messages = result["messages"]
    last_message = messages[-1]

    response_text = extract_content(last_message)
    usage = extract_usage(messages)
    accumulate_usage(usage)

    return ChatResponse(
        response=response_text,
        thread_id=payload.thread_id,
        usage=usage,
    )


@app.get("/usage/", response_model=UsageStats)
def usage_stats():
    """
    Return cumulative token usage and cost since the server last started.

    Useful for monitoring how many tokens the clinic owner is spending
    per session. Resets to zero on every server restart.
    """
    pricing_is_configured = (
        INPUT_TOKEN_PRICE_PER_1K > 0 or OUTPUT_TOKEN_PRICE_PER_1K > 0
    )

    return UsageStats(
        **_usage,
        pricing_configured=pricing_is_configured,
    )


@app.post("/webhook/extension/")
def ingest_message(payload: RawMessageIn, db: Session = Depends(get_session)):
    """
    Receive a single WhatsApp message from the Chrome extension and save it.

    Skips the message silently if an identical one already exists in the
    database (same chat, sender, text, and timestamp).

    Args:
        payload: The message data sent by the extension.
        db:      SQLAlchemy session injected by FastAPI.
    """
    duplicate = (
        db.query(RawMessage)
        .filter(
            RawMessage.chat_name == payload.chat_name,
            RawMessage.sender == payload.sender,
            RawMessage.text == payload.text,
            RawMessage.timestamp == payload.timestamp,
        )
        .first()
    )

    if duplicate:
        return {"status": "already_exists", "message_id": duplicate.id}

    new_message = RawMessage(
        chat_name=payload.chat_name,
        sender=payload.sender,
        text=payload.text,
        timestamp=payload.timestamp,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    print(f"Ingested message #{new_message.id}: [{payload.sender}] {payload.text[:60]}")
    return {"status": "received", "message_id": new_message.id}


@app.post("/webhook/extension/batch/")
def ingest_batch(payload: RawMessageBatchIn, db: Session = Depends(get_session)):
    """
    Receive a batch of WhatsApp messages from the Chrome extension.

    Deduplication is done in memory rather than with one DB query per
    message. We load all existing messages for the relevant chats once,
    build a set of signatures, then only insert messages whose signature
    is not already in the set.

    Args:
        payload: A list of messages sent by the extension.
        db:      SQLAlchemy session injected by FastAPI.

    Returns:
        The number of messages actually inserted (duplicates are skipped).
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
