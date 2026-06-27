import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.tools import execute_sql_query, generate_report

tools = [execute_sql_query, generate_report]

"""
Right now the agent is not self correcting meaning that if it threw a wrong query
it won't fix it self
do we need a multi-step self correcting agent? idk
"""


# Shared checkpointer — keeps conversation memory across requests as long
# as the server process is running.
agent_checkpointer = MemorySaver()

SYSTEM_PROMPT = """You are a veterinary clinic assistant.
You answer the clinic owner's questions by querying a SQLite database of
WhatsApp group chat messages.

Database table: raw_messages
Columns: id, chat_name, sender, text, timestamp, captured_at

Steps (use tools in this order when needed):
1. execute_sql_query — run your SQL SELECT first
2. generate_report — only if user explicitly asks for a report

Rules:
- Use LIKE with wildcards for text searches (e.g. WHERE text LIKE '%Rocky%').
- Use GROUP BY and COUNT for summaries.
- For "total donations" use SUM on numeric values in text.
- Only report what the database returns. Never invent data — including row counts, names, or amounts.
- If SQL errors, fix and retry.
- Keep answers short and conversational. Exception: when the user asks to "show" or "see" messages, include the actual message content (sender, text snippet, date) inline rather than just summarizing.
- For report requests: query data first, then call generate_report.
- IMPORTANT: When you call generate_report, do NOT repeat the data in your
  text reply. The UI already shows the report as a preview card. Just confirm
  in one sentence that the report is ready (e.g. "Your attendance report is ready.").

Examples:
- Q: "Did Dr. Faraz treat Max?" → SELECT * FROM raw_messages WHERE sender LIKE '%Faraz%' AND text LIKE '%Max%' AND chat_name LIKE 'TEST_%'
- Q: "Total donations from Mrs. Fatima" → SELECT text FROM raw_messages WHERE text LIKE '%Mrs. Fatima%' AND text LIKE '%PKR%' AND chat_name LIKE 'TEST_%'
- Q: "Generate a donation report" → query donations, then call generate_report(report_type='donation_ledger', ...), then reply with one sentence only."""

"""All of the build model functios are same we can literally creata  model class here and save
al ot lines of code and make this file less messy."""


def build_ollama_model(base_url: str, model_name: str, api_key: str):
    """
    Create a ChatOllama or ChatOpenAI client for an Ollama endpoint.

    Ollama exposes two API flavours:
    - Native Ollama API  (no '/v1' in the URL) → use ChatOllama
    - OpenAI-compatible  ('/v1' in the URL)    → use ChatOpenAI

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


def build_openai_model():
    """
    Create a standard OpenAI ChatOpenAI client as a fallback provider.

    Reads OPENAI_API_KEY and DEFAULT_MODEL from the environment.

    Returns:
        A ChatOpenAI instance pointed at the OpenAI API.
    """
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
        temperature=0.2,
    )


def build_gemini_model(api_key: str, model_name: str):
    """
    Create a ChatGoogleGenerativeAI client for the Google Gemini API.

    Uses the Gemini Developer API (not Vertex AI). The API key is read from
    GOOGLE_API_KEY (or GEMINI_API_KEY as fallback) in the environment.

    Args:
        api_key:    Google AI API key from Google AI Studio.
        model_name: The Gemini model identifier (e.g. 'gemini-2.0-flash').

    Returns:
        A ChatGoogleGenerativeAI instance ready for use.
    """
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
    )


def build_groq_model(api_key: str, model_name: str):
    """
    Create a ChatOpenAI client for the Groq API.

    Groq exposes an OpenAI-compatible endpoint so we use ChatOpenAI with
    a custom base URL. No extra package is needed.

    Args:
        api_key:    Groq API key from https://console.groq.com/keys.
        model_name: The Groq model identifier (e.g. 'llama-3.3-70b-versatile').

    Returns:
        A ChatOpenAI instance pointed at the Groq API.
    """
    return ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        model=model_name,
        temperature=0.2,
    )


def build_mistral_model(api_key: str, model_name: str):
    """
    Create a ChatOpenAI client for the Mistral API.

    Mistral exposes an OpenAI-compatible endpoint so we use ChatOpenAI with
    a custom base URL. No extra package is needed.

    Args:
        api_key:    Mistral API key from https://console.mistral.ai.
        model_name: The Mistral model identifier (e.g. 'mistral-small-latest').

    Returns:
        A ChatOpenAI instance pointed at the Mistral API.
    """
    return ChatOpenAI(
        base_url="https://api.mistral.ai/v1",
        api_key=api_key,
        model=model_name,
        temperature=0.2,
    )


def build_cerebras_model(api_key: str, model_name: str):
    """
    Create a ChatOpenAI client for the Cerebras API.

    Cerebras exposes an OpenAI-compatible endpoint so we use ChatOpenAI with
    a custom base URL. No extra package is needed.

    Args:
        api_key:    Cerebras API key from https://console.cerebras.ai.
        model_name: The Cerebras model identifier (e.g. 'llama-3.3-70b').

    Returns:
        A ChatOpenAI instance pointed at the Cerebras API.
    """
    return ChatOpenAI(
        base_url="https://api.cerebras.ai/v1",
        api_key=api_key,
        model=model_name,
        temperature=0.2,
    )


def build_openrouter_model(api_key: str, model_name: str):
    """
    Create a ChatOpenAI client for the OpenRouter API.

    OpenRouter exposes an OpenAI-compatible endpoint that aggregates many
    free models from multiple providers. We use ChatOpenAI with a custom
    base URL. No extra package is needed.

    Args:
        api_key:    OpenRouter API key from https://openrouter.ai/keys.
        model_name: The model identifier (e.g. 'auto:free' for smart routing).

    Returns:
        A ChatOpenAI instance pointed at the OpenRouter API.
    """
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        model=model_name,
        temperature=0.2,
        default_headers={"HTTP-Referer": "https://vetlog.app"},
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

    if provider == "groq":
        return build_groq_model(
            api_key=os.getenv("GROQ_API_KEY", ""),
            model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        )

    if provider == "mistral":
        return build_mistral_model(
            api_key=os.getenv("MISTRAL_API_KEY", ""),
            model_name=os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
        )

    if provider == "cerebras":
        return build_cerebras_model(
            api_key=os.getenv("CEREBRAS_API_KEY", ""),
            model_name=os.getenv("CEREBRAS_MODEL", "llama-3.3-70b"),
        )

    if provider == "openrouter":
        return build_openrouter_model(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            model_name=os.getenv("OPENROUTER_MODEL", "auto:free"),
        )

    return build_openai_model()


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
