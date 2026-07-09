import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import trim_messages # Reduce token usage for conversation histor
from app.tools import execute_sql_query, generate_report
from datetime import datetime
tools = [execute_sql_query, generate_report]

"""
Right now the agent is not self correcting meaning that if it threw a wrong query
it won't fix it self
do we need a multi-step self correcting agent? idk
"""


# Shared checkpointer — keeps conversation memory across requests as long
# as the server process is running.
agent_checkpointer = MemorySaver()

def get_system_prompt() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""You are a veterinary clinic assistant for Vetlog AI.
        Today's date: {today}

        RULES (follow exactly, no exceptions):
        - Call execute_sql_query on EVERY response before replying.
        - Never use general knowledge or training data to answer.
        - For out-of-scope questions (e.g. "Who is the president?"): run
        SELECT 'out_of_scope' AS reason, then reply only:
        "I can only answer questions about the clinic's WhatsApp data."

        Database table: raw_messages
        Columns: id, chat_name, sender, text, timestamp, captured_at
        Timestamps: ISO-8601 format (YYYY-MM-DD HH:MM:SS)

        Tool order:
        1. execute_sql_query — always first
        2. generate_report — only if user explicitly asks for a report

        Query rules:
        - Text search: WHERE text LIKE '%term%'
        - Summaries: GROUP BY + COUNT or SUM
        - Date ranges: WHERE timestamp >= date('{today}', '-7 days')
        - Only report what the DB returns. Never invent data.
        - On SQL error: fix and retry.
        - After generate_report: confirm in one sentence only. Do not repeat the data.

        Examples:
        - Q: "Did Dr. Faraz treat Max?" → SELECT * FROM raw_messages WHERE sender LIKE '%Faraz%' AND text LIKE '%Max%'
        - Q: "What happened today?" → SELECT * FROM raw_messages WHERE timestamp >= '{today} 00:00:00' AND timestamp <= '{today} 23:59:59'
        - Q: "Who is the president?" → SELECT 'out_of_scope' AS reason → reply with refusal only
        - Q: "Last 7 days messages" → SELECT * FROM raw_messages WHERE timestamp >= date('{today}', '-7 days')
        """

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
        "openai": None  # Uses the default OpenAI URL
    }
    
    return ChatOpenAI(
        base_url=base_urls.get(provider),
        api_key=api_key,
        model=model_name,
        temperature=0.2,
        default_headers={"HTTP-Referer": "https://vetlog.app"} if provider == "openrouter" else None
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
        "openai": "OPENAI"
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
        model_name=model_name
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

    trimmer = trim_messages(
    max_tokens=3000,          # hard ceiling for history sent to the model
    strategy="last",          # keep the most recent messages, not the oldest
    token_counter=chat_model, # uses the actual model's tokeniser for accuracy
    include_system=True,      # always keep the system prompt
    allow_partial=False,      # never send a half-cut message
    start_on="human",         # trimmed history must start with a user message
    )
    
    agent_graph = create_react_agent(
        model=chat_model,
        tools=tools,
        checkpointer=agent_checkpointer,
        prompt=get_system_prompt(),
        messages_modifier=trimmer,
    )

    #Message modifier allows for a hard limit on the tokens used by model in input prompt for context generation
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
