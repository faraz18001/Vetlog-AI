import os

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.tools import execute_sql_query

tools = [execute_sql_query]

# Shared checkpointer — keeps conversation memory across requests as long
# as the server process is running.
agent_checkpointer = MemorySaver()

SYSTEM_PROMPT = """You are a veterinary clinic assistant.
You answer the clinic owner's questions by querying a SQLite database of
WhatsApp group chat messages.

Database table: raw_messages
Columns: id, chat_name, sender, text, timestamp, captured_at

Rules:
- Always use a single SQL query. Never call the tool more than once per question.
- Use LIKE with wildcards for text searches (e.g. WHERE text LIKE '%Rocky%').
- Use GROUP BY and COUNT when the question asks for summaries or counts.
- Only report what the database actually returns. Never invent data.
- Keep answers short and conversational."""


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


def get_llm_model():
    """
    Factory that picks and configures the right LLM based on .env settings.

    Reads AGENT_PROVIDER to decide which provider to use:
    - 'ollama' (default): Ollama Cloud or a local Ollama server.
    - anything else: falls back to the standard OpenAI API.

    Returns:
        A configured LangChain chat model instance.
    """
    provider = os.getenv("AGENT_PROVIDER", "ollama").lower()

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        return build_ollama_model(base_url, model_name, api_key)

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


if __name__ == "__main__":
    for tool in tools:
        print(f"{tool.name}: {tool.description}\n")
