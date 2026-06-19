import os
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


import sqlite3
from urllib.parse import urlparse

from app.config import DATABASE_URL


def _get_db_path() -> str:
    parsed = urlparse(DATABASE_URL)
    path = parsed.path
    if path.startswith("/"):
        path = path.lstrip("/")
    return path or "vetlog.db"


DB_PATH = _get_db_path()


@tool
def sql_db_list_tables() -> str:
    """Input is an empty string, output is a comma-separated list of tables in the database."""
    con = sqlite3.connect(DB_PATH)
    try:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [
            row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")
        ]
        return ", ".join(tables)
    finally:
        con.close()


@tool
def sql_db_schema(table_names: str) -> str:
    """Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.
    Be sure that the tables actually exist by calling sql_db_list_tables first!
    Example Input: table1, table2, table3"""
    con = sqlite3.connect(DB_PATH)
    try:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        valid_tables = {
            row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")
        }
        results = []
        for table in table_names.split(","):
            table = table.strip()
            if table not in valid_tables:
                results.append(
                    f"Error: table_names {{{table!r}}} not found in database"
                )
                continue
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                (table,),
            )
            schema_row = cursor.fetchone()
            if schema_row:
                results.append(schema_row[0])
                try:
                    quoted_table = '"' + table.replace('"', '""') + '"'
                    cursor.execute(f"SELECT * FROM {quoted_table} LIMIT 3;")
                    rows = cursor.fetchall()
                    if rows:
                        col_names = [
                            description[0] for description in cursor.description
                        ]
                        results.append(
                            f"/*\n3 rows from {table} table:\n"
                            + "\t".join(col_names)
                            + "\n"
                            + "\n".join("\t".join(str(x) for x in row) for row in rows)
                            + "\n*/"
                        )
                except Exception as e:
                    results.append(f"Error fetching sample rows: {e}")
        return "\n\n".join(results)
    finally:
        con.close()


@tool
def sql_db_query(query: str) -> str:
    """Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields."""
    con = sqlite3.connect(DB_PATH)
    try:
        cursor = con.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        return str(res)
    except Exception as e:
        return f"Error: {e}"
    finally:
        con.close()


tools = [sql_db_list_tables, sql_db_schema, sql_db_query]

if __name__ == "__main__":
    for t in tools:
        print(f"{t.name}: {t.description}\n")


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
SYSTEM_PROMPT = "You are a helpful veterinary assistant. Use the tools available to answer questions about the database."


def initialize_agent():
    chat_model = get_llm_model()
    agent_graph = create_react_agent(
        model=chat_model,
        tools=tools,
        checkpointer=agent_check_pointer,
        prompt=SYSTEM_PROMPT,
    )
    return agent_graph
