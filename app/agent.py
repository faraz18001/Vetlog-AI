import os
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.tools import (
    execute_sql_query,
    generate_dynamic_report,
    generate_static_report,
    query_to_inline_table,
)

tools = [
    execute_sql_query,
    query_to_inline_table,
    generate_static_report,
    generate_dynamic_report,
]

"""
Right now the agent is not self correcting meaning that if it threw a wrong query
it won't fix it self
do we need a multi-step self correcting agent? idk
"""


# Shared checkpointer — keeps conversation memory across requests as long
# as the server process is running.
agent_checkpointer = MemorySaver()

SYSTEM_PROMPT = (
    f"""You are a veterinary clinic assistant.
You answer the clinic owner's questions by querying a SQLite database of
WhatsApp group chat messages.

Today's date: {datetime.now().strftime("%Y-%m-%d")}

Database table: raw_messages
Columns: id, chat_name, sender, text, timestamp, captured_at

Steps (use tools in this order when needed):
1. execute_sql_query — run your SQL SELECT first (for counts, sums, lookups, yes/no questions). Caps at 10 rows.
2. query_to_inline_table — when the user wants to SEE all rows or a full dataset (e.g. "show all", "list every", "all 150 donations"). This tool writes the full unbounded result to a file and the UI renders it inline — no row limit.
3. generate_static_report — only if the user explicitly asks for a report that fits a standard category (daily_summary, donation_ledger, treatment_log, attendance_sheet).
4. generate_dynamic_report — when the user asks for a custom report that does NOT fit a standard template. Write the full Markdown content yourself with any structure.

Rules:
- Use LIKE with wildcards for text searches (e.g. WHERE text LIKE '%Rocky%').
- Use GROUP BY and COUNT for summaries.
- For "total donations" use SUM on numeric values in text.
- Only report what the database returns. Never invent data — including row counts, names, or amounts.
- If SQL errors, fix and retry.
- Use execute_sql_query for counts/sums/lookups (max 10 rows shown). Use query_to_inline_table when the user wants to SEE many rows or the full dataset (e.g. "show all", "list every", "every donation from June").
- Keep answers short and conversational. Exception: when the user asks to "show" or "see" messages, include the actual message content (sender, text snippet, date) inline rather than just summarizing.
- After query_to_inline_table, do NOT repeat the rows in your text reply. The UI shows the full table inline. Just state the row count and a one-line summary (e.g. "Here are all 150 donations from June.").
- For report requests: query data first, then call generate_static_report (for standard templates) or generate_dynamic_report (for custom reports).
- IMPORTANT: When you call generate_static_report, generate_dynamic_report, or query_to_inline_table, do NOT repeat the data in your
  text reply. The UI already shows the report/table as a preview card. Just confirm
  in one sentence that the report is ready (e.g. "Your attendance report is ready.").
- For reports about a specific date: ALWAYS pass the date parameter to generate_static_report
  (e.g. date='2026-03-27') so the title and filename use the report's subject date, not today.
- For reports: SELECT specific columns (chat_name, sender, text, timestamp). Omit id and captured_at.
- Write a meaningful 2-3 sentence summary for the summary parameter when calling generate_static_report.
- For reports that need ALL matching data (treatment timelines, detailed reports): call
  execute_sql_query(query=..., limit=100) with ORDER BY timestamp to get up to 100 rows.
  Then pass that data to generate_dynamic_report or generate_static_report.
- When writing reports with 20+ rows: group entries by week or condition instead of
  listing every single row. Use the full data to produce an informative summary — never
  abbreviate rows with "..." or "(continued)" placeholders.

Examples:
- Q: "Did Dr. Faraz treat Max?" → SELECT * FROM raw_messages WHERE sender LIKE '%Faraz%' AND text LIKE '%Max%' AND chat_name LIKE 'TEST_%'
- Q: "Total donations from Mrs. Fatima" → SELECT text FROM raw_messages WHERE text LIKE '%Mrs. Fatima%' AND text LIKE '%PKR%' AND chat_name LIKE 'TEST_%'
- Q: "Show me all donations from June" → call query_to_inline_table(query='SELECT * FROM raw_messages WHERE text LIKE '%PKR%' AND timestamp LIKE '2025-06%', title='All Donations from June')
- Q: "Generate a donation report" → query donations, then call generate_static_report(report_type='donation_ledger', ...), then reply with one sentence only.
- Q: "Create a treatment timeline for Rocky with notes" → query Rocky messages, then call generate_dynamic_report(title='Rocky Treatment Timeline', content='## Timeline\n\n...'), then reply with one sentence only.
- Q: "Generate a daily summary report for March 27" → SELECT chat_name, sender, text, timestamp FROM raw_messages WHERE timestamp LIKE '2026-03-27%' → generate_static_report(report_type='daily_summary', title='March 27 Clinic Activity', data=..., summary='X patients treated, Y staff on duty. Key events: ...', date='2026-03-27')
- Q: "Generate a report for Oreo with treatment notes" → execute_sql_query(query='SELECT chat_name, sender, text, timestamp FROM raw_messages WHERE text LIKE '%Oreo%' ORDER BY timestamp', limit=100) → generate_dynamic_report(title='Oreo Treatment Report', content=...)

"""
    """All of the build model functios are same we can literally creata  model class here and save
al ot lines of code and make this file less messy."""
)


def build_ollama_model(base_url: str, model_name: str, api_key: str):
    """
    Create a ChatOllama or ChatOpenAI client for an Ollama endpoint.

    Ollama exposes two API flavours:
    - Native Ollama API  (no '/v1' in the URL) - use ChatOllama
    - OpenAI-compatible  ('/v1' in the URL)    - use ChatOpenAI

    Args:
        base_url:   The base URL of the Ollama server.
        model_name: The model identifier (e.g. 'gpt-oss:20b-cloud').
        api_key:    Bearer token for authenticated Ollama Cloud endpoints.

    Returns:
        A LangChain chat model instance ready for use.
    """
    is_openai_compatible = "v1" in base_url

    if is_openai_compatible:
        # Use the OpenAI-compatible client. If no key is supplied, pass the
        # string "ollama" as a placeholder (the library requires a non-empty value).
        effective_key = api_key if api_key else "ollama"
        return ChatOpenAI(
            base_url=base_url,
            api_key=effective_key,
            model=model_name,
            temperature=0.2,
        )

    # Native Ollama client. Attach the bearer token as a header if provided.
    client_kwargs = {}
    if api_key:
        client_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}

    return ChatOllama(
        base_url=base_url,
        model=model_name,
        temperature=0.2,
        client_kwargs=client_kwargs if client_kwargs else None,
    )


def build_openai_compatible_model(provider: str, api_key: str, model_name: str):
    """
    Create a ChatOpenAI client for any OpenAI-compatible API endpoint.

    Args:
        provider:   The provider name (e.g. 'groq', 'mistral', 'openrouter', 'openai').
        api_key:    The API key for the provider.
        model_name: The model identifier to use.

    Returns:
        A ChatOpenAI instance pointed at the correct API.
    """
    base_urls = {
        "groq": "https://api.groq.com/openai/v1",
        "mistral": "https://api.mistral.ai/v1",
        "cerebras": "https://api.cerebras.ai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "openai": None,  # Uses the default OpenAI URL
    }

    return ChatOpenAI(
        base_url=base_urls.get(provider),
        api_key=api_key,
        model=model_name,
        temperature=0.2,
        default_headers={"HTTP-Referer": "https://vetlog.app"}
        if provider == "openrouter"
        else None,
    )


def build_gemini_model(api_key: str, model_name: str):
    """
    Create a ChatGoogleGenerativeAI client for the Google Gemini API.
    """
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
    )


def get_llm_model():
    """
    Factory that picks and configures the right LLM based on .env settings.

    Reads AGENT_PROVIDER to decide which provider to use:
    - 'ollama' (default): Ollama Cloud or a local Ollama server.
    - 'gemini':           Google Gemini via the Gemini Developer API.
    - 'groq':             Groq via its OpenAI-compatible endpoint.
    - 'mistral':          Mistral via its OpenAI-compatible endpoint.
    - 'cerebras':         Cerebras via its OpenAI-compatible endpoint.
    - 'openrouter':       OpenRouter via its OpenAI-compatible endpoint.
    - anything else:      falls back to the standard OpenAI API.

    Returns:
        A configured LangChain chat model instance.
    """
    provider = os.getenv("AGENT_PROVIDER", "ollama").lower()

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        return build_ollama_model(base_url, model_name, api_key)

    if provider == "gemini":
        return build_gemini_model(
            api_key=os.getenv("GOOGLE_API_KEY", ""),
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        )

    # For all other OpenAI-compatible providers, grab their specific env vars
    env_prefixes = {
        "groq": "GROQ",
        "mistral": "MISTRAL",
        "cerebras": "CEREBRAS",
        "openrouter": "OPENROUTER",
        "openai": "OPENAI",
    }

    prefix = env_prefixes.get(provider, "OPENAI")

    if prefix == "OPENAI":
        api_key = os.getenv("OPENAI_API_KEY", "")
        model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
    else:
        api_key = os.getenv(f"{prefix}_API_KEY", "")
        model_name = os.getenv(f"{prefix}_MODEL", "")

    return build_openai_compatible_model(
        provider=provider if provider in env_prefixes else "openai",
        api_key=api_key,
        model_name=model_name,
    )


def initialize_agent():
    """
    Build and return the LangGraph ReAct agent.

    The agent is given the SQL tool and the system prompt, and uses the
    shared MemorySaver checkpointer so conversation history is preserved
    between requests (keyed by thread_id).

    Returns:
        A compiled LangGraph agent graph ready to call .invoke() on.
    """
    chat_model = get_llm_model()

    agent_graph = create_react_agent(
        model=chat_model,
        tools=tools,
        checkpointer=agent_checkpointer,
        prompt=SYSTEM_PROMPT,
    )

    return agent_graph


_agent_instance = None


def get_current_agent():
    """Returns the singleton agent instance, initializing it if necessary."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = initialize_agent()
    return _agent_instance


def reload_agent():
    """Forces the agent to re-initialize with the current environment variables."""
    global _agent_instance
    _agent_instance = initialize_agent()
    return _agent_instance


if __name__ == "__main__":
    for tool in tools:
        print(f"{tool.name}: {tool.description}\n")
