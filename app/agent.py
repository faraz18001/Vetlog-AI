import os
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.tools import execute_sql_query


tools = [execute_sql_query]


def get_llm_model():
    """
    Decoupled factory to instantiate the ChatModel based on .env config.
    Supports native ChatOllama and OpenAI-compatible ChatOpenAI endpoints.
    """
    provider = os.getenv("AGENT_PROVIDER", "ollama").lower()
    base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
    api_key = os.getenv("OLLAMA_API_KEY", "")

    if provider == "ollama":
        if "v1" in base_url:
            # OpenAI-compatible API Endpoint
            return ChatOpenAI(
                base_url=base_url,
                api_key=api_key if api_key else "ollama",
                model=model_name,
                temperature=0.2,
            )
        else:
            # Native Ollama API
            client_kwargs = {}
            if api_key:
                client_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}

            return ChatOllama(
                base_url=base_url,
                model=model_name,
                temperature=0.2,
                client_kwargs=client_kwargs if client_kwargs else None,
            )
    else:
        # Fallback to standard OpenAI GPT-4o if configured
        openai_key = os.getenv("OPENAI_API_KEY", "")
        return ChatOpenAI(
            api_key=openai_key,
            model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
            temperature=0.2,
        )


agent_check_pointer = MemorySaver()

SCHEMA = "raw_messages(id INTEGER, chat_name VARCHAR, sender VARCHAR, text TEXT, timestamp VARCHAR, captured_at DATETIME)"

SYSTEM_PROMPT = f"""You are a veterinary assistant that answers questions by querying a database of veterinary group chat messages.
Schema: {SCHEMA}.
Use LIKE for fuzzy text search. Call execute_sql_query with your SQL, then answer naturally from the results. Never make up data."""


def initialize_agent():
    chat_model = get_llm_model()
    agent_graph = create_react_agent(
        model=chat_model,
        tools=tools,
        checkpointer=agent_check_pointer,
        prompt=SYSTEM_PROMPT,
    )
    return agent_graph


if __name__ == "__main__":
    for t in tools:
        print(f"{t.name}: {t.description}\n")
