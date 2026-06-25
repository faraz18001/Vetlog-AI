import os
import sqlite3
from urllib.parse import urlparse

from langchain_core.tools import tool

from app.config import DATABASE_URL


def _resolve_db_path() -> str:
    """
    Convert the DATABASE_URL from config into an absolute file path.

    SQLite URLs look like 'sqlite:///vetlog.db' or 'sqlite:////abs/path.db'.
    urlparse gives us the path portion. If it is relative, we resolve it
    against the project root (one directory above this file's package).

    Returns:
        The absolute path to the SQLite database file.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parsed = urlparse(DATABASE_URL)
    db_path = parsed.path

    # urlparse includes a leading slash for absolute paths — strip it for
    # relative paths so os.path.join works correctly.
    if db_path.startswith("/"):
        db_path = db_path.lstrip("/")

    if os.path.isabs(db_path):
        return db_path

    resolved = os.path.join(project_root, db_path)

    # Fall back to a sensible default if the URL was empty or malformed.
    if not resolved:
        return os.path.join(project_root, "vetlog.db")

    return resolved


DB_PATH = _resolve_db_path()


@tool
def execute_sql_query(query: str) -> str:
    """
    Execute a read-only SQL query against the Vetlog SQLite database.

    The database has one table — raw_messages — which stores WhatsApp
    messages scraped from the clinic's group chats. Use this tool after
    writing the correct SQL for the user's question. If the query fails,
    the error message is returned so you can fix and retry.

    Args:
        query: A valid SQLite SELECT statement.

    Returns:
        A tab-separated string of results (header row + data rows),
        'No results found.' if the query matched nothing,
        or an error message if the query was invalid.
    """
    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return "No results found."

        # Build a tab-separated table: header row then data rows.
        column_names = [description[0] for description in cursor.description]
        header = "\t".join(column_names)

        # Cap results at 10 rows to keep the response concise.
        MAX_ROWS = 10
        data_rows = []
        for row in rows[:MAX_ROWS]:
            data_rows.append("\t".join(str(cell) for cell in row))

        result = header + "\n" + "\n".join(data_rows)

        if len(rows) > MAX_ROWS:
            result += f"\n... and {len(rows) - MAX_ROWS} more rows"

        return result

    except Exception as error:
        return f"Error: {error}"

    finally:
        connection.close()
