import os
import sqlite3
from urllib.parse import urlparse

from langchain_core.tools import tool
from app.config import DATABASE_URL


def _get_db_path() -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parsed = urlparse(DATABASE_URL)
    path = parsed.path
    if path.startswith("/"):
        path = path.lstrip("/")
    resolved = os.path.join(project_root, path) if not os.path.isabs(path) else path
    return resolved or os.path.join(project_root, "vetlog.db")


DB_PATH = _get_db_path()


@tool
def execute_sql_query(query: str) -> str:
    """Execute a raw SQL query on the vetlog database and return the results.
    The database has a single table called 'raw_messages' that stores veterinary group chat messages.
    Use this tool after you have generated the correct SQL for the user's question.
    If the query fails, an error message is returned — rewrite and retry."""
    con = sqlite3.connect(DB_PATH)
    try:
        cursor = con.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            return "No results found."
        col_names = [description[0] for description in cursor.description]
        header = "\t".join(col_names)
        data = "\n".join("\t".join(str(x) for x in row) for row in rows)
        return f"{header}\n{data}"
    except Exception as e:
        return f"Error: {e}"
    finally:
        con.close()
