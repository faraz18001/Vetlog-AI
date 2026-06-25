import json
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.agent import initialize_agent
from app.config import INPUT_TOKEN_PRICE_PER_1K, OUTPUT_TOKEN_PRICE_PER_1K
from app.database import RawMessage, get_session, init_db
from app.schemas import (
    AgentStep,
    ChatRequest,
    ChatResponse,
    RawMessageBatchIn,
    RawMessageIn,
    TokenUsage,
    UsageStats,
    LLMConfigResponse,
    LLMConfigUpdate,
)
from app.tools import REPORTS_DIR
from app.config_manager import update_env_file

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


@app.get("/api/config/llm", response_model=LLMConfigResponse)
def get_llm_config():
    """Return the currently configured LLM provider and model (without the API key)."""
    provider = os.getenv("AGENT_PROVIDER", "ollama").lower()
    provider_upper = provider.upper()
    
    if provider_upper == "GEMINI":
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    elif provider_upper == "OPENAI":
        model = os.getenv("DEFAULT_MODEL", "gpt-4o")
    else:
        model = os.getenv(f"{provider_upper}_MODEL", "")
        
    return LLMConfigResponse(provider=provider, model=model)


@app.post("/api/config/llm")
def set_llm_config(payload: LLMConfigUpdate):
    """
    Update the active LLM provider, save to .env, and hot-reload the agent.
    WARNING: Hot-reloading wipes the short-term conversation memory of the current session.
    """
    update_env_file(payload.provider, payload.model, payload.api_key)
    
    # Hot reload the global agent so it picks up the new environment variables
    global _agent
    _agent = initialize_agent()
    print(f"[Vetlog] Agent re-initialized with provider: {payload.provider}")
    
    return {"status": "success"}


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
    returns an answer. Token usage and agent step chain are tracked
    per request and returned to the frontend.

    Args:
        payload: Contains the user's message and a thread_id for
                 conversation memory.

    Returns:
        The agent's response text, token usage data, optional report
        path, and a list of intermediate agent steps.
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
    report_path = find_report_path(messages)
    steps = extract_steps(messages)

    return ChatResponse(
        response=response_text,
        thread_id=payload.thread_id,
        usage=usage,
        report_path=report_path,
        steps=steps,
    )


@app.post("/chat/stream/")
async def chat_stream(payload: ChatRequest):
    """
    Stream the agent's execution as Server-Sent Events (SSE).

    Emits three types of events while the agent runs:
      - {"type": "step",  "label": str, "detail": str}  — a tool-call step
      - {"type": "chunk", "text":  str}                  — a text token of the final answer
      - {"type": "done",  "usage": {...}, "report_path": str|null}

    The frontend reads this stream and:
      1. Appends each step to the step chain in real-time.
      2. Streams the answer text as chunks arrive (no separate typeout needed).
      3. Attaches usage/report metadata when the done event fires.
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialised yet.")

    config = {"configurable": {"thread_id": payload.thread_id}}

    async def event_generator():
        report_path = None
        total_input = 0
        total_output = 0

        # Text chunks are buffered while tools are in flight.
        # They are flushed only after the last tool_end, so the step
        # chain always completes before the answer starts appearing.
        text_buffer: list[str] = []
        tools_in_flight = 0  # incremented on_tool_start, decremented on_tool_end
        tools_ever_started = False  # True once any tool_start fires
        text_flushed = (
            False  # True after the buffer has been flushed for the first time
        )

        async def flush_text_buffer():
            """Yield all buffered text chunks, clear the buffer, and mark as flushed."""
            nonlocal text_flushed
            for chunk_text in text_buffer:
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk_text})}\n\n"
            text_buffer.clear()
            text_flushed = True

        try:
            async for event in _agent.astream_events(
                {"messages": [("user", payload.message)]},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                # Tool is about to run
                if kind == "on_tool_start":
                    tools_in_flight += 1
                    tools_ever_started = True
                    tool_name = event.get("name", "")

                    if tool_name == "execute_sql_query":
                        tool_input = event.get("data", {}).get("input", {}) or {}
                        query = tool_input.get("query", "")
                        yield f"data: {json.dumps({'type': 'step', 'label': 'Querying database', 'detail': query[:120]})}\n\n"

                    elif tool_name == "generate_report":
                        tool_input = event.get("data", {}).get("input", {}) or {}
                        title = tool_input.get("title", "")
                        yield f"data: {json.dumps({'type': 'step', 'label': 'Generating report', 'detail': title})}\n\n"

                    else:
                        yield f"data: {json.dumps({'type': 'step', 'label': f'Running {tool_name}', 'detail': ''})}\n\n"

                # Tool finished
                elif kind == "on_tool_end":
                    tools_in_flight -= 1
                    raw_output = event.get("data", {}).get("output", "") or ""

                    # LangGraph may wrap the tool return value in a ToolMessage
                    # object. Extract the plain string content from it.
                    if hasattr(raw_output, "content"):
                        output = raw_output.content or ""
                        if isinstance(output, list):
                            output = " ".join(
                                b.get("text", "") if isinstance(b, dict) else str(b)
                                for b in output
                            )
                    elif isinstance(raw_output, str):
                        output = raw_output
                    else:
                        output = str(raw_output)

                    if output.startswith("Error:"):
                        yield f"data: {json.dumps({'type': 'step', 'label': 'Query failed', 'detail': ''})}\n\n"

                    elif output.startswith("reports/"):
                        report_path = output
                        yield f"data: {json.dumps({'type': 'step', 'label': 'Report saved', 'detail': ''})}\n\n"

                    elif output == "No results found.":
                        yield f"data: {json.dumps({'type': 'step', 'label': '0 rows returned', 'detail': ''})}\n\n"

                    else:
                        # Count data rows (lines minus the TSV header row)
                        lines = [l for l in output.strip().splitlines() if l.strip()]
                        row_count = max(0, len(lines) - 1)
                        label = (
                            f"{row_count} row{'s' if row_count != 1 else ''} returned"
                        )
                        yield f"data: {json.dumps({'type': 'step', 'label': label, 'detail': ''})}\n\n"

                    # If no more tools are running, flush buffered text now so
                    # the answer starts streaming right after the last step.
                    if tools_in_flight == 0:
                        async for sse in flush_text_buffer():
                            yield sse

                # LLM is streaming its final answer
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is None:
                        continue

                    # Skip chunks that contain tool call artifacts — these are
                    # not real text and would appear as garbled JSON in the answer.
                    tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
                    if tool_call_chunks:
                        continue

                    content = getattr(chunk, "content", "")

                    texts: list[str] = []
                    if isinstance(content, str) and content:
                        texts.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                t = block.get("text", "")
                                if t:
                                    texts.append(t)

                    for t in texts:
                        should_buffer = (
                            tools_ever_started  # tools have run or are running
                            and (
                                tools_in_flight > 0  # a tool is still active
                                or not text_flushed
                            )  # or flush hasn't happened yet
                        )
                        if should_buffer:
                            text_buffer.append(t)
                        else:
                            # Direct answer (no tools), or post-flush streaming
                            yield f"data: {json.dumps({'type': 'chunk', 'text': t})}\n\n"

                # Collect token usage from LLM call ends
                elif kind == "on_chat_model_end":
                    meta = event.get("data", {}).get("output")
                    usage_meta = getattr(meta, "usage_metadata", None) if meta else None
                    if usage_meta:
                        total_input += usage_meta.get("input_tokens", 0)
                        total_output += usage_meta.get("output_tokens", 0)

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            return

        # Flush anything left (safety net — normally empty by this point)
        async for sse in flush_text_buffer():
            yield sse

        # Final done event
        input_cost = (total_input / 1000) * INPUT_TOKEN_PRICE_PER_1K
        output_cost = (total_output / 1000) * OUTPUT_TOKEN_PRICE_PER_1K
        usage = {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "cost_usd": round(input_cost + output_cost, 6),
        }
        accumulate_usage(TokenUsage(**usage))

        yield f"data: {json.dumps({'type': 'done', 'thread_id': payload.thread_id, 'report_path': report_path, 'usage': usage})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def find_report_path(messages: list) -> str | None:
    """
    Scan the agent's message list for a ToolMessage that contains a report path.

    When the agent calls generate_report, LangGraph stores the tool's return
    value in a ToolMessage. The return value is always 'reports/<filename>.md',
    so we look for exactly that pattern.

    Args:
        messages: The full message list returned by agent.invoke().

    Returns:
        The report path string (e.g. 'reports/daily_summary_2025-06-25.md')
        or None if no report was generated this turn.
    """
    for message in messages:
        # ToolMessages carry the raw return value of each tool call.
        class_name = type(message).__name__
        if class_name != "ToolMessage":
            continue

        content = getattr(message, "content", "")
        if (
            isinstance(content, str)
            and content.startswith("reports/")
            and content.endswith(".md")
        ):
            return content

    return None


def extract_steps(messages: list) -> list[AgentStep]:
    """
    Walk the LangGraph message list and build a step chain for the frontend.

    The ReAct agent produces a repeating pattern of:
      AIMessage (with tool_calls)  →  ToolMessage (with the tool's output)

    This function translates each pair into a human-readable AgentStep:
    - For an AIMessage that contains tool_calls, we emit a "Running SQL" or
      "Generating report" step showing the tool input as the detail.
    - For the matching ToolMessage we emit a "returned N rows" or error step
      showing a short preview of what the tool returned.
    - The final AIMessage (the plain text answer) is NOT included because the
      frontend already renders it as the main reply bubble.

    Args:
        messages: The full message list returned by agent.invoke().

    Returns:
        A list of AgentStep objects ordered chronologically.
    """
    steps = []

    for message in messages:
        class_name = type(message).__name__

        if class_name == "AIMessage":
            tool_calls = getattr(message, "tool_calls", []) or []
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})

                if tool_name == "execute_sql_query":
                    query = tool_args.get("query", "").strip()
                    # Trim very long queries to keep the UI tidy
                    short_query = query[:120] + "…" if len(query) > 120 else query
                    steps.append(
                        AgentStep(
                            label="Running SQL",
                            detail=short_query,
                        )
                    )

                elif tool_name == "generate_report":
                    title = tool_args.get("title", "")
                    report_type = tool_args.get("report_type", "")
                    steps.append(
                        AgentStep(
                            label="Generating report",
                            detail=f"{report_type}: {title}" if title else report_type,
                        )
                    )

                else:
                    # Generic fallback for any future tools
                    steps.append(
                        AgentStep(
                            label=f"Calling {tool_name}",
                            detail=str(tool_args)[:120],
                        )
                    )

        elif class_name == "ToolMessage":
            content = getattr(message, "content", "") or ""

            if isinstance(content, str) and content.startswith("Error:"):
                steps.append(
                    AgentStep(
                        label="Tool call failed",
                        detail=content[:120],
                    )
                )
            elif isinstance(content, str) and content.startswith("reports/"):
                steps.append(
                    AgentStep(
                        label="Report saved",
                        detail=content,
                    )
                )
            else:
                # Count the number of data rows returned (header + rows)
                lines = [l for l in content.strip().splitlines() if l.strip()]
                row_count = max(0, len(lines) - 1)  # subtract header row
                preview = lines[0][:80] if lines else ""
                label = f"{row_count} row{'s' if row_count != 1 else ''} returned"
                steps.append(
                    AgentStep(
                        label=label,
                        detail=preview,
                    )
                )

    return steps


@app.get("/reports/{filename}")
def get_report_content(filename: str):
    """
    Return the markdown content of a saved report as JSON.

    The frontend fetches this to render an inline preview inside the chat.

    Args:
        filename: The report's base filename (e.g. 'daily_summary_2025-06-25.md').
    """
    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found.")

    with open(filepath, "r") as f:
        content = f.read()

    return {"filename": filename, "content": content}


@app.get("/reports/{filename}/export", response_class=HTMLResponse)
def export_report_html(filename: str):
    """
    Return the report as a styled, print-ready HTML page.

    The frontend opens this in a new browser tab. The page is styled with
    print CSS so the user can press Ctrl+P → Save as PDF to get a clean PDF
    without requiring any server-side PDF library.

    Args:
        filename: The report's base filename (e.g. 'daily_summary_2025-06-25.md').
    """
    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found.")

    with open(filepath, "r") as f:
        md_content = f.read()

    try:
        import markdown as md_lib

        body_html = md_lib.markdown(md_content, extensions=["tables", "fenced_code"])
    except ImportError:
        # If the markdown library isn't installed, wrap the raw text in a <pre>.
        body_html = f"<pre>{md_content}</pre>"

    report_title = filename.replace("_", " ").replace(".md", "").title()

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>{report_title}</title>
      <style>
        body {{
          font-family: 'Segoe UI', Arial, sans-serif;
          max-width: 820px;
          margin: 48px auto;
          padding: 0 24px;
          color: #1a1a1a;
          line-height: 1.7;
        }}
        h1, h2, h3 {{ font-weight: 600; margin-top: 1.5em; }}
        h2 {{ font-size: 1.5rem; border-bottom: 2px solid #e5e5e5; padding-bottom: 8px; }}
        h3 {{ font-size: 1.15rem; }}
        table {{
          width: 100%;
          border-collapse: collapse;
          margin: 1.25em 0;
          font-size: 0.9rem;
        }}
        th {{
          background: #f4f4f5;
          font-weight: 600;
          text-align: left;
          padding: 10px 14px;
          border: 1px solid #d4d4d8;
        }}
        td {{
          padding: 8px 14px;
          border: 1px solid #e4e4e7;
          vertical-align: top;
        }}
        tr:nth-child(even) td {{ background: #fafafa; }}
        hr {{ border: none; border-top: 1px solid #e5e5e5; margin: 2em 0; }}
        em {{ color: #71717a; font-size: 0.875rem; }}
        code {{ background: #f4f4f5; padding: 2px 6px; border-radius: 4px; }}
        @media print {{
          body {{ margin: 24px; }}
          @page {{ margin: 2cm; }}
        }}
      </style>
    </head>
    <body>
      {body_html}
      <script>
        // Auto-open the print dialog so the user can save directly as PDF.
        window.onload = function() {{ window.print(); }};
      </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


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
