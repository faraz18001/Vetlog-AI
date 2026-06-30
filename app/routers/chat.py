import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import ChatRequest, ChatResponse, TokenUsage, UsageStats, AgentStep
from app.config import INPUT_TOKEN_PRICE_PER_1K, OUTPUT_TOKEN_PRICE_PER_1K
from app.agent import get_current_agent

router = APIRouter(prefix="", tags=["chat"])


def _sse(payload: dict) -> str:
    """Format a dict as a Server-Sent-Events `data:` line."""
    return f"data: {json.dumps(payload)}\n\n"


def _tool_output_str(raw_output) -> str:
    """Normalise a tool's raw output into a plain string."""
    if hasattr(raw_output, "content"):
        output = raw_output.content or ""
        if isinstance(output, list):
            output = " ".join(
                b.get("text", "") if isinstance(b, dict) else str(b) for b in output
            )
        return output
    if isinstance(raw_output, str):
        return raw_output
    return str(raw_output)


def _iter_chunk_texts(content) -> list[str]:
    """Extract plain text pieces from a streaming chunk's content."""
    texts: list[str] = []
    if isinstance(content, str):
        if content:
            texts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text", "")
                if t:
                    texts.append(t)
    return texts


# In-memory usage accumulator
_usage = {
    "total_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0,
}

def extract_content(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        else:
            parts.append(block.get("text", ""))
    return " ".join(parts)

def extract_usage(messages: list) -> TokenUsage:
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

def find_report_path(messages: list) -> str | None:
    for message in messages:
        if type(message).__name__ != "ToolMessage":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.startswith("reports/") and content.endswith(".md"):
            return content
    return None

def find_table_path(messages: list) -> str | None:
    """Find the file path from a query_to_inline_table tool call.

    The tool's output looks like:
        reports/query_2025-06-30_143022.md
        Rows: 150
        Title: All Donations from June

    We extract just the first line (the path).
    """
    for message in messages:
        if type(message).__name__ != "ToolMessage":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.startswith("reports/") and "Rows:" in content:
            return content.splitlines()[0].strip()
    return None

def extract_steps(messages: list) -> list[AgentStep]:
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
                    short_query = query[:120] + "…" if len(query) > 120 else query
                    steps.append(AgentStep(label="Running SQL", detail=short_query))
                elif tool_name == "query_to_inline_table":
                    query = tool_args.get("query", "").strip()
                    short_query = query[:120] + "…" if len(query) > 120 else query
                    steps.append(AgentStep(label="Querying full dataset", detail=short_query))
                elif tool_name == "generate_report":
                    title = tool_args.get("title", "")
                    report_type = tool_args.get("report_type", "")
                    steps.append(AgentStep(label="Generating report", detail=f"{report_type}: {title}" if title else report_type))
                else:
                    steps.append(AgentStep(label=f"Calling {tool_name}", detail=str(tool_args)[:120]))
        elif class_name == "ToolMessage":
            content = getattr(message, "content", "") or ""
            if isinstance(content, str) and content.startswith("Error:"):
                steps.append(AgentStep(label="Tool call failed", detail=content[:120]))
            elif isinstance(content, str) and content.startswith("reports/") and "Rows:" in content:
                first_line = content.splitlines()[0].strip()
                steps.append(AgentStep(label="Table saved", detail=first_line))
            elif isinstance(content, str) and content.startswith("reports/"):
                steps.append(AgentStep(label="Report saved", detail=content))
            else:
                lines = [l for l in content.strip().splitlines() if l.strip()]
                row_count = max(0, len(lines) - 1)
                preview = lines[0][:80] if lines else ""
                label = f"{row_count} row{'s' if row_count != 1 else ''} returned"
                steps.append(AgentStep(label=label, detail=preview))
    return steps

@router.post("/chat/", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    agent = get_current_agent()
    config = {"configurable": {"thread_id": payload.thread_id}}
    result = agent.invoke({"messages": [("user", payload.message)]}, config=config)
    messages = result["messages"]
    last_message = messages[-1]

    response_text = extract_content(last_message)
    usage = extract_usage(messages)
    accumulate_usage(usage)
    report_path = find_report_path(messages)
    table_path = find_table_path(messages)
    steps = extract_steps(messages)

    return ChatResponse(
        response=response_text,
        thread_id=payload.thread_id,
        usage=usage,
        report_path=report_path,
        table_path=table_path,
        steps=steps,
    )

@router.post("/chat/stream/")
async def chat_stream(payload: ChatRequest):
    agent = get_current_agent()
    config = {"configurable": {"thread_id": payload.thread_id}}

    async def event_generator():
        report_path = None
        table_path = None
        total_input = 0
        total_output = 0

        try:
            async for event in agent.astream_events(
                {"messages": [("user", payload.message)]},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name == "execute_sql_query":
                        tool_input = event.get("data", {}).get("input", {}) or {}
                        query = tool_input.get("query", "")
                        yield _sse({"type": "step", "label": "Querying database", "detail": query[:120]})
                    elif tool_name == "query_to_inline_table":
                        tool_input = event.get("data", {}).get("input", {}) or {}
                        query = tool_input.get("query", "")
                        yield _sse({"type": "step", "label": "Querying full dataset", "detail": query[:120]})
                    elif tool_name == "generate_report":
                        tool_input = event.get("data", {}).get("input", {}) or {}
                        title = tool_input.get("title", "")
                        yield _sse({"type": "step", "label": "Generating report", "detail": title})
                    else:
                        yield _sse({"type": "step", "label": f"Running {tool_name}", "detail": ""})

                elif kind == "on_tool_end":
                    output = _tool_output_str(event.get("data", {}).get("output", ""))

                    if output.startswith("Error:"):
                        yield _sse({"type": "step", "label": "Query failed", "detail": ""})
                    elif output.startswith("reports/") and "Rows:" in output:
                        table_path = output.splitlines()[0].strip()
                        yield _sse({"type": "step", "label": "Table saved", "detail": ""})
                    elif output.startswith("reports/"):
                        report_path = output
                        yield _sse({"type": "step", "label": "Report saved", "detail": ""})
                    elif output == "No results found.":
                        yield _sse({"type": "step", "label": "0 rows returned", "detail": ""})
                    else:
                        lines = [l for l in output.strip().splitlines() if l.strip()]
                        row_count = max(0, len(lines) - 1)
                        label = f"{row_count} row{'s' if row_count != 1 else ''} returned"
                        yield _sse({"type": "step", "label": label, "detail": ""})

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is None:
                        continue
                    # Skip chunks that only carry tool-call deltas — we want text.
                    if getattr(chunk, "tool_call_chunks", None):
                        continue
                    for t in _iter_chunk_texts(getattr(chunk, "content", "")):
                        yield _sse({"type": "chunk", "text": t})

                elif kind == "on_chat_model_end":
                    meta = event.get("data", {}).get("output")
                    usage_meta = getattr(meta, "usage_metadata", None) if meta else None
                    if usage_meta:
                        total_input += usage_meta.get("input_tokens", 0)
                        total_output += usage_meta.get("output_tokens", 0)

        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        input_cost = (total_input / 1000) * INPUT_TOKEN_PRICE_PER_1K
        output_cost = (total_output / 1000) * OUTPUT_TOKEN_PRICE_PER_1K
        usage = {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "cost_usd": round(input_cost + output_cost, 6),
        }
        accumulate_usage(TokenUsage(**usage))
        yield _sse({
            "type": "done",
            "thread_id": payload.thread_id,
            "report_path": report_path,
            "table_path": table_path,
            "usage": usage,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@router.get("/usage/", response_model=UsageStats)
def usage_stats():
    pricing_is_configured = (INPUT_TOKEN_PRICE_PER_1K > 0 or OUTPUT_TOKEN_PRICE_PER_1K > 0)
    return UsageStats(
        **_usage,
        pricing_configured=pricing_is_configured,
    )
