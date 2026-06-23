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

SCHEMA_DESCRIPTION = """
Table: raw_messages

Columns:
  id          INTEGER PRIMARY KEY   — Auto-incrementing message ID
  chat_name   VARCHAR NOT NULL       — Name of the WhatsApp group chat (e.g. "Vetlog Group", "Vetlog Clinical Group")
  sender      VARCHAR NOT NULL       — Person who sent the message (e.g. "Dr. Faraz", "Nurse Ali", "Dr. Sarah Jenkins")
  text        TEXT NOT NULL          — Message content (treatment notes, diagnoses, medication logs, status updates)
  timestamp   VARCHAR NOT NULL       — Human-readable timestamp (e.g. "5:20 PM, 6/9/2026")
  captured_at DATETIME               — When the message was ingested into the system

Example rows:
  id=1   chat_name="Vetlog Group"          sender="Dr. Faraz"        text="Treated the puppy"
  id=3   chat_name="Vetlog Group"          sender="Dr. Faraz"        text="Yellowish puppy is recovering"
  id=9   chat_name="Vetlog Clinical Group"  sender="You"              text="Treated Rocky (Dog (German Shepherd)) at 1:00 PM.\nStatus: Treatment log updated.\nDiagnosis: Gastrointestinal Infection.\nOwner: John Smith."
  id=10  chat_name="Vetlog Clinical Group"  sender="Dr. Sarah Jenkins" text="Administered medication: Metoclopramide to Bella (Dog (Golden Retriever)).\nOwner: Sarah Miller. Dosage: 2 tab(s).\nStatus: Completed successfully."
"""

SYSTEM_PROMPT = f"""You are a veterinary assistant that answers questions by querying a database of veterinary group chat messages.
{SCHEMA_DESCRIPTION}
Follow these steps for every user question:

1. **UNDERSTAND** — Parse the user's natural language question. Identify key entities (animal, symptom, treatment, doctor, date, etc.).
2. **GENERATE SQL** — Write a SQLite query against the `raw_messages` table that answers the question. Use LIKE for text searches, and consider searching both the `sender` and `text` columns where appropriate.
3. **EXECUTE** — Call the `execute_sql_query` tool with your generated SQL.
4. **ANSWER** — Read the results and respond in clear, conversational natural language. If no results match, say so politely.

Guidelines:
- Always use LIKE with wildcards for fuzzy text matching (e.g. WHERE text LIKE '%yellowish%').
- Use OR to search multiple columns where relevant (e.g. WHERE sender LIKE '%Faraz%' OR text LIKE '%Faraz%').
- Use strftime or string comparison on the timestamp column if date filtering is needed.
- If a query returns an error, fix the SQL and try again.
- Never make up data — only report what the database returns.
- Keep answers concise but informative, quoting the relevant message text when appropriate."""


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
