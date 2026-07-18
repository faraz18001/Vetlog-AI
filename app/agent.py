import os
from datetime import datetime

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, HarnessProfile, register_harness_profile

# Exclude built-in filesystem, shell, and sub-agent tools — we only need
# our SQL tools + the built-in write_todos (planning).
_vetlog_profile = HarnessProfile(
    excluded_tools=frozenset([
        "ls", "read_file", "write_file", "edit_file",
        "glob", "grep", "execute", "task",
    ])
)
for _provider in ("google_genai", "openai", "ollama", "default"):
    register_harness_profile(_provider, _vetlog_profile)

from app.tools import (
    execute_sql_query,
    generate_dynamic_report,
    generate_static_report,
    query_to_inline_table,
    execute_python_analytics,
)

tools = [
    execute_sql_query,
    query_to_inline_table,
    generate_static_report,
    generate_dynamic_report,
    execute_python_analytics,
]

"""
Right now the agent is not self correcting meaning that if it threw a wrong query
it won't fix it self
do we need a multi-step self correcting agent? idk
"""


# Shared checkpointer — persists conversation memory to the main database
# so agent state survives server restarts.
# Initialised during FastAPI lifespan (async); referenced by initialize_agent().
_agent_checkpointer = None


async def init_checkpointer():
    """Create the shared AsyncSqliteSaver — called once during app startup."""
    global _agent_checkpointer
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "vetlog.db",
    )
    conn = await aiosqlite.connect(db_path)
    _agent_checkpointer = AsyncSqliteSaver(conn=conn)


def get_system_prompt() -> str:
    """Build the system prompt with the current date injected dynamically."""
    return f"""You are a veterinary clinic assistant. Answer by querying a SQLite database of WhatsApp group chat messages.

Today's date: {datetime.now().strftime("%Y-%m-%d")}

Database: raw_messages — columns: id, chat_name, sender, text, timestamp, captured_at
Timestamps are ISO-8601 strings (YYYY-MM-DD HH:MM:SS). Use BETWEEN for date ranges, not LIKE patterns.
  Example: WHERE timestamp BETWEEN '2026-04-01' AND '2026-04-30 23:59:59'

WORKFLOW — plan first, then execute step by step. You can call tools as many times as needed.

Step 1 — Peek: Always run ONE SELECT LIMIT 5 first to see the data format.
  Example: SELECT chat_name, text FROM raw_messages LIMIT 5

Step 2 — Plan: Based on what you saw, decide which queries answer the question.
  Simple (count, yes/no): 1 query.  Complex (compare, breakdown): 2-3 queries.

Step 3 — Execute: Run each query. Use one result to shape the next.
  For clinical: WHERE chat_name LIKE '%Clinical%'
  For donations: WHERE chat_name LIKE '%Donations%'
  For attendance: WHERE chat_name LIKE '%Attendance%'

Step 4 — Answer: Short direct answer. Only generate reports when asked.

Rules:
- Never invent data. If SQL errors, fix and retry.
- When counting things: use COUNT(*). When grouping: use GROUP BY.
- Do NOT guess values in UNION ALL or OR chains. If data cannot be grouped natively in SQLite because it is unstructured text, use the execute_python_analytics tool.
- If a query returns the '100 row limit' warning, DO NOT paginate using OFFSET. If you need all the data, use query_to_inline_table instead.
- Keep answers short. Reply with numbers, not walls of text.

Examples of multi-step:
Q: "How many treatments did Oreo have?"
Step 1: SELECT text FROM raw_messages WHERE chat_name LIKE '%Clinical%' AND text LIKE '%Oreo%' LIMIT 5
Step 2: SELECT COUNT(*) FROM raw_messages WHERE chat_name LIKE '%Clinical%' AND text LIKE '%Oreo%'
Step 3: Answer — "Oreo had 4 treatments."

Q: "Who are our top 3 most frequent donors?"
Step 1: SELECT text FROM raw_messages WHERE chat_name LIKE '%Donations%' LIMIT 5
Step 2: execute_python_analytics(query="SELECT text FROM raw_messages WHERE chat_name LIKE '%Donations%'", python_script="counts = {{}}\\nfor r in rows:\\n  if 'JDC' in r['text']: counts['JDC Foundation'] = counts.get('JDC Foundation', 0) + 1\\n  elif 'Saylani' in r['text']: counts['Saylani'] = counts.get('Saylani', 0) + 1\\nfor k,v in counts.items(): print(f'{{k}}: {{v}}')")
Step 3: Answer — "JDC Foundation is the top donor."
"""


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
        if api_key:
            effective_key = api_key
        else:
            effective_key = "ollama"
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

    if client_kwargs:
        kwargs_for_call = client_kwargs
    else:
        kwargs_for_call = None

    return ChatOllama(
        base_url=base_url,
        model=model_name,
        temperature=0.2,
        client_kwargs=kwargs_for_call,
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
        "opencode": "https://opencode.ai/zen/v1",
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


def get_llm_model(user_config=None):
    """
    Factory that picks and configures the right LLM.

    If user_config is provided (from per-user DB settings), use those values.
    Otherwise fall back to .env for backward compatibility.

    Args:
        user_config: Optional dict with keys 'provider', 'model', 'api_key'.

    Returns:
        A configured LangChain chat model instance.
    """
    if user_config:
        provider = user_config["provider"].lower()
        model_name = user_config["model"]
        api_key = user_config.get("api_key", "")
    else:
        provider = os.getenv("AGENT_PROVIDER", "ollama").lower()
        model_name = None
        api_key = ""

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        if not model_name:
            model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
        if not api_key and not user_config:
            api_key = os.getenv("OLLAMA_API_KEY", "")
        return build_ollama_model(base_url, model_name, api_key)

    if provider == "gemini":
        if not model_name:
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        if not api_key and not user_config:
            api_key = os.getenv("GOOGLE_API_KEY", "")
        return build_gemini_model(
            api_key=api_key,
            model_name=model_name,
        )

    # For all other OpenAI-compatible providers
    env_prefixes = {
        "groq": "GROQ",
        "mistral": "MISTRAL",
        "cerebras": "CEREBRAS",
        "openrouter": "OPENROUTER",
        "opencode": "OPENCODE",
        "openai": "OPENAI",
    }

    if not model_name:
        prefix = env_prefixes.get(provider, "OPENAI")
        if prefix == "OPENAI":
            model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
        else:
            model_name = os.getenv(f"{prefix}_MODEL", "")

    if not api_key and not user_config:
        prefix = env_prefixes.get(provider, "OPENAI")
        if prefix == "OPENAI":
            api_key = os.getenv("OPENAI_API_KEY", "")
        else:
            api_key = os.getenv(f"{prefix}_API_KEY", "")

    if provider in env_prefixes:
        resolved_provider = provider
    else:
        resolved_provider = "openai"

    return build_openai_compatible_model(
        provider=resolved_provider,
        api_key=api_key,
        model_name=model_name,
    )


def initialize_agent(user_config=None):
    """
    Build and return the LangGraph deep agent.

    Accepts an optional user_config dict (provider, model, api_key) from
    per-user settings. Falls back to .env if not provided.

    Returns:
        A compiled LangGraph agent graph ready to call .invoke() on.
    """
    chat_model = get_llm_model(user_config)

    agent_graph = create_deep_agent(
        model=chat_model,
        tools=tools,
        system_prompt=get_system_prompt(),
        checkpointer=_agent_checkpointer,
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
