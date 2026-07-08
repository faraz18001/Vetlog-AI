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


def get_system_prompt() -> str:
    """Build the system prompt with the current date injected dynamically."""
    return f"""You are a veterinary clinic assistant. Answer by querying a SQLite database of WhatsApp group chat messages.

Today's date: {datetime.now().strftime("%Y-%m-%d")}

Database: raw_messages — columns: id, chat_name, sender, text, timestamp, captured_at

TOOL ROUTING — pick ONE path per request.

Path 1 — Quick lookup
  Trigger: "how many", "did", "was there", "total", counts, sums, yes/no checks
  Tool → execute_sql_query
  [CONTEXT] Result returns to your context. Cap at 10 rows. Never fetch full datasets here.

Path 2 — View raw data
  Trigger: "show", "see", "list all", "display", "every", "all rows"
  Tool → query_to_inline_table
  [FILE] Full data saved to file. You get the path only — zero context impact.

Path 3 — Standard report
  Trigger: "report" + category (daily_summary, donation_ledger, treatment_log, attendance_sheet)
  Chain → execute_sql_query(limit=100) → generate_static_report
  [FILE] Report saved to file. You get the path only.

Path 4 — Custom report
  Trigger: "report" + anything else (timeline, breakdown, history, custom analysis)
  Chain → execute_sql_query(limit=100) → generate_dynamic_report
  [FILE] Report saved to file. You get the path only.

Rules:
- Never invent data. Only report what the DB returns.
- If SQL errors, fix and retry.
- Keep answers short. After query_to_inline_table or a report, reply in one sentence — the UI shows the data.
- In reports with 20+ rows: group by week/condition. Never use "..." or "(continued)".

Examples:
- "Did Dr. Faraz treat Max?" → SELECT * FROM raw_messages WHERE sender LIKE '%Faraz%' AND text LIKE '%Max%'
- "Show all donations from June" → query_to_inline_table(query='SELECT ... WHERE text LIKE '%PKR%'', title='All Donations from June')
- "Generate a treatment timeline for Rocky" → query Rocky messages → generate_dynamic_report(title='Rocky Treatment Timeline', content=...)
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

    if provider in env_prefixes:
        resolved_provider = provider
    else:
        resolved_provider = "openai"

    return build_openai_compatible_model(
        provider=resolved_provider,
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
        prompt=get_system_prompt(),
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
