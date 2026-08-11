import contextlib
import io
import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

from langchain_core.tools import tool

from app.config import DATABASE_URL


# =============================================================================
# GUARDRAILS — Security hardening for SQL and Python execution tools
# =============================================================================

# P0: SQL allowlist — only these tables are accessible
SQL_ALLOWED_TABLES = frozenset({"raw_messages"})

# P0: Blocked SQL keywords (any statement type that isn't SELECT)
SQL_BLOCKED_KEYWORDS = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
    "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX",
})

# P0: Blocked path patterns for Python file access
FILE_BLOCKED_PATTERNS = (
    r"\.env$",
    r"\.db$",
    r"\.sqlite$",
    r"\.key$",
    r"\.pem$",
    r"\.json$",
    r"\.ya?ml$",
    r"\.toml$",
    r"\.ini$",
    r"\.cfg$",
    r"/etc/",
    r"/home/",
    r"/root/",
    r"/var/",
    r"credentials",
    r"secrets",
    r"password",
    r"secret",
    r"token",
    r"api_key",
    r"apikey",
)

# P0: Allowed Python modules in the sandbox
PYTHON_ALLOWED_MODULES = frozenset({
    "pandas", "pd", "re", "sqlite3", "vetlog_parser",
    "io", "contextlib", "json", "math", "datetime",
    "collections", "itertools", "statistics", "functools",
    "operator", "string", "textwrap", "typing",
    "decimal", "fractions", "numbers", "random", "hashlib",
    "copy", "pprint", "csv", "itertools",
})

# P0: Blocked Python builtins
PYTHON_BLOCKED_BUILTINS = frozenset({
    "open", "exec", "eval", "compile", "__import__",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit",
    "help", "input", "print",  # print replaced with custom capture
    "memoryview", "type",
})

# P1: Credential redaction patterns
CREDENTIAL_PATTERNS = [
    (r'(API_KEY|APIKEY|TOKEN|SECRET|PASSWORD|PASSWORD)\s*[=:]\s*["\']?([^\s"\']+)', r'\1=***REDACTED***'),
    (r'(Bearer|Basic)\s+[A-Za-z0-9+/=]{20,}', r'\1 ***REDACTED***'),
    (r'[a-zA-Z0-9_-]*key[a-zA-Z0-9_-]*\s*[=:]\s*["\']?[A-Za-z0-9_\-./+=]{16,}', r'***REDACTED***'),
    (r'lsv2_[a-z]{2}_[a-f0-9]{40,}', r'***REDACTED***'),
]

# P1: Row limits
SQL_MAX_ROWS = 50
QUERY_TABLE_MAX_ROWS = 200


def _validate_sql(query: str) -> str | None:
    """
    Validate a SQL query against the guardrails.
    Returns None if valid, or an error message string if blocked.
    """
    # Normalize
    cleaned = query.strip().rstrip(";")

    # Reject multiple statements (semicolon chaining)
    if ";" in cleaned:
        return "Error: Multiple SQL statements are not allowed."

    # Parse with sqlglot
    try:
        parsed = sqlglot.parse(cleaned, read="sqlite")
    except Exception as e:
        return f"Error: Could not parse SQL query: {e}"

    if not parsed or parsed[0] is None:
        return "Error: Could not parse SQL query."

    statement = parsed[0]

    # Must be a SELECT statement
    if not isinstance(statement, sqlglot.exp.Select):
        stmt_type = type(statement).__name__
        return f"Error: Only SELECT queries are allowed. Got: {stmt_type}"

    # Extract table references
    tables = set()
    for table_expr in statement.find_all(sqlglot.exp.Table):
        tables.add(table_expr.name.lower())

    # Check table allowlist
    disallowed = tables - SQL_ALLOWED_TABLES
    if disallowed:
        return (
            f"Error: Access denied to table(s): {', '.join(disallowed)}. "
            f"Allowed tables: {', '.join(sorted(SQL_ALLOWED_TABLES))}"
        )

    # Check for blocked keywords in raw text (defense in depth)
    upper_cleaned = cleaned.upper()
    for keyword in SQL_BLOCKED_KEYWORDS:
        if keyword in upper_cleaned:
            return f"Error: SQL keyword '{keyword}' is not permitted."

    # Block multiple table references (JOINs, cartesian products) — DoS prevention
    from_clauses = list(statement.find_all(sqlglot.exp.From))
    join_clauses = list(statement.find_all(sqlglot.exp.Join))
    if len(from_clauses) > 1 or len(join_clauses) > 0:
        return "Error: JOINs and multiple table references are not allowed. Query a single table."

    return None  # Valid


def _sanitize_python_script(script: str) -> str | None:
    """
    Check a Python script for dangerous patterns.
    Returns None if safe, or an error message string if blocked.
    """
    # Check for dangerous import attempts
    import_patterns = [
        r'^\s*import\s+(\w+)',
        r'^\s*from\s+(\w+)',
    ]
    for pattern in import_patterns:
        for match in re.finditer(pattern, script, re.MULTILINE):
            module = match.group(1).split(".")[0]
            if module not in PYTHON_ALLOWED_MODULES:
                return f"Error: Import of module '{module}' is not allowed."

    # Check for open() calls (file access)
    if re.search(r'\bopen\s*\(', script):
        return "Error: File operations (open) are not permitted in the sandbox."

    # Check for blocked builtins (print is allowed — it's replaced with a safe version)
    blocked_for_check = PYTHON_BLOCKED_BUILTINS - {"print"}
    for builtin in blocked_for_check:
        if re.search(rf'\b{builtin}\s*\(', script):
            return f"Error: Function '{builtin}' is not permitted in the sandbox."

    # Check for path traversal attempts
    for pattern in FILE_BLOCKED_PATTERNS:
        if re.search(pattern, script, re.IGNORECASE):
            return "Error: Access to system paths and sensitive files is blocked."

    # Block infinite loops and resource exhaustion
    if re.search(r'\bwhile\s+True\s*:', script):
        return "Error: Infinite loops (while True) are not permitted in the sandbox."

    if re.search(r'\bfor\s+\w+\s+in\s+range\s*\(\s*\d{6,}\s*\)', script):
        return "Error: Excessively large loops are not permitted in the sandbox."

    return None  # Safe


def _redact_credentials(text: str) -> str:
    """
    Redact credentials and sensitive data from tool output.
    """
    result = text
    for pattern, replacement in CREDENTIAL_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


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

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "reports"
)
os.makedirs(REPORTS_DIR, exist_ok=True)
"""Right now the report templates are hardcoded but what if i wanted a freeflow report then what?"""
_REPORT_TEMPLATES = {
    "daily_summary": "## Daily Clinic Summary — {date}\n\n{summary}\n\n### {title}\n\n{table}\n\n---\n*Generated by Vetlog AI Assistant*",
    "donation_ledger": "## Donation Ledger — {date}\n\n{summary}\n\n### {title}\n\n{table}\n\n---\n*Generated by Vetlog AI Assistant*",
    "treatment_log": "## Treatment Log — {date}\n\n{summary}\n\n### {title}\n\n{table}\n\n---\n*Generated by Vetlog AI Assistant*",
    "attendance_sheet": "## Attendance Sheet — {date}\n\n{summary}\n\n### {title}\n\n{table}\n\n---\n*Generated by Vetlog AI Assistant*",
}


def _tsv_to_markdown_table(data: str) -> str:
    """Convert tab-separated data into a GitHub-flavoured markdown table."""
    lines = data.strip().split("\n")
    if not lines:
        return "_No data._"

    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        rows.append(line.split("\t"))

    md = "| " + " | ".join(header) + " |\n"

    sep = "| "
    for i in range(len(header)):
        if i > 0:
            sep += " | "
        sep += "---"
    sep += " |\n"
    md += sep

    for row in rows:
        md += "| " + " | ".join(row) + " |\n"

    return md


def _rows_with_display_timestamps(column_names, rows):
    """
    Convert ISO-8601 timestamps (24-hour) to 12-hour AM/PM format
    for display. Keeps 24-hour storage intact for SQL range queries.
    """
    if not rows:
        return rows

    ts_idx = None
    idx = 0
    for col in column_names:
        if col.lower() == "timestamp":
            ts_idx = idx
            break
        idx += 1

    if ts_idx is None:
        return rows

    formatted = []
    for row in rows:
        new_row = list(row)
        cell_val = new_row[ts_idx]
        if cell_val is not None:
            val = str(cell_val)
        else:
            val = ""
        if val.startswith("202"):
            try:
                dt = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                new_row[ts_idx] = dt.strftime("%b %d, %Y %I:%M %p")
            except ValueError:
                pass
        formatted.append(tuple(new_row))
    return formatted


@tool
def generate_static_report(
    report_type: str,
    title: str,
    query: str,
    summary: str = "",
    date: str = "",
) -> str:
    """
    Generate a formatted Markdown report using a predefined template and save it.

    1. Use this when the user's report request fits one of the 4 standard
    2. categories: daily_summary, donation_ledger, treatment_log, or attendance_sheet.
    3. For reports about a specific date: ALWAYS pass the date parameter to generate_static_report
      (e.g. date='2026-03-27') so the title and filename use the report's subject date, not today.
    4. Provide the exact SQL query in the 'query' parameter (e.g. SELECT sender, text, timestamp FROM raw_messages...).
       The tool will execute the query and format the results directly. Omit id and captured_at.

    Call this tool when the user asks for a structured report. The report is written to 
    the reports/ directory and its filename is returned — the UI will display the markdown.
    
    IMPORTANT: DO NOT use this tool if you are also calling query_to_inline_table 
    or generate_dynamic_report. Choose EXACTLY ONE reporting tool to display data.

    IMPORTANT: When you call generate_static_report, do NOT repeat the data in your
      text reply. Just confirm in one sentence that the report is ready.

    Args:
        report_type: One of 'daily_summary', 'donation_ledger', 'treatment_log', 'attendance_sheet'.
        title:       A short human-readable title for the report (e.g. 'June 24 Clinic Activity').
        query:       The exact SQLite SELECT query to fetch the report data.
        summary:     A 2-3 sentence summary of what the report contains (patient count, key events, totals).
        date:        The SUBJECT date of the report (e.g. '2026-03-27'), NOT today's date.

    Returns:
        The filename of the saved report.
    """
    if report_type not in _REPORT_TEMPLATES:
        template_keys = ""
        for key in _REPORT_TEMPLATES:
            if template_keys:
                template_keys += ", "
            template_keys += key
        return (
            "Error: Unknown report_type '"
            + report_type
            + "'. Choose from: "
            + template_keys
        )

    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        rows = _rows_with_display_timestamps(column_names, rows)
        
        data_lines = []
        for row in rows:
            data_lines.append("\t".join(str(cell) for cell in row))
        tsv = "\t".join(column_names) + "\n" + "\n".join(data_lines) if data_lines else "No results found."
        table_md = _tsv_to_markdown_table(tsv) if data_lines else "_No data found for this query._"
    except Exception as e:
        return f"Error executing query for report: {e}"
    finally:
        connection.close()

    date_str = date or datetime.now().strftime("%Y-%m-%d")

    safe_title = title.lower().replace(" ", "_")[:30]
    filename = f"{report_type}_{date_str}_{safe_title}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    template = _REPORT_TEMPLATES[report_type]
    if summary:
        final_summary = summary
    else:
        final_summary = "Report: " + title
    content = template.format(
        date=date_str,
        title=title,
        table=table_md,
        summary=final_summary,
    )

    with open(filepath, "w") as f:
        f.write(content)

    return f"reports/{filename}"


@tool
def generate_dynamic_report(title: str, content: str) -> str:
    """
    Save a free-form Markdown report to a file.

    1. Use this when the user's request does NOT fit a standard template.
    2. Write the full Markdown content yourself — any structure, any format.
    3. For standard categories (daily_summary, donation_ledger, treatment_log,
    attendance_sheet), use generate_static_report instead.
    4. When writing reports with 20+ rows: group entries by week or condition instead of
      listing every single row. Use the full data to produce an informative summary — never
      abbreviate rows with "..." or "(continued)" placeholders.

    IMPORTANT: When you call generate_dynamic_report, do NOT repeat the data in your
      text reply. The UI already shows the report/table as a preview card. Just confirm
      in one sentence that the report is ready (e.g. "Your treatment history report is ready.").

    Args:
        title:   A short human-readable title for the report
                 (e.g. 'Rocky Treatment History').
        content: The full Markdown content of the report.

    Returns:
        The filename of the saved report (e.g. 'reports/rocky_treatment_2025-06-25.md').
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.lower().replace(" ", "_").replace("/", "_")[:30]
    filename = f"{safe_title}_{date_str}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"## {title}\n\n*Generated {date_str}*\n\n{content}\n")

    return f"reports/{filename}"


"""We might need a detailed report tool we already have one that gives concise
but what if the dude asks a detailed report then we might have to give it to them"""


@tool
def execute_sql_query(query: str) -> str:
    """
    Execute a read-only SQL query against the Vetlog SQLite database.

    The database has one table — raw_messages — which stores WhatsApp
    messages scraped from the clinic's group chats. Use this tool after
    writing the correct SQL for the user's question. If the query fails,
    the error message is returned so you can fix and retry.

    SQL patterns for this DB:
    - Use LIKE with wildcards for text searches (e.g. WHERE text LIKE '%Rocky%')
    - Use GROUP BY and COUNT for summaries
    - Never invent data — only return what the query actually finds
    - Default chat names in the DB follow a prefix pattern; use LIKE for matching
    - This tool returns a MAXIMUM OF 100 ROWS. If you need fewer rows, use LIMIT in your SQL.
    - If you hit the 100-row limit and need all the data, DO NOT paginate with OFFSET. Use query_to_inline_table.

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

        column_names = []
        for description in cursor.description:
            column_names.append(description[0])
        header = "\t".join(column_names)
        MAX_ROWS = 100
        data_rows = []
        for row in rows[:MAX_ROWS]:
            row_str = ""
            for cell in row:
                if row_str:
                    row_str += "\t"
                row_str += str(cell)
            data_rows.append(row_str)

        result = header + "\n" + "\n".join(data_rows)

        if len(rows) > MAX_ROWS:
            result += f"\n... and {len(rows) - MAX_ROWS} more rows"

        return result

    except Exception as error:
        return f"Error: {error}"

    finally:
        connection.close()


@tool
def query_to_inline_table(query: str, title: str = "Query Results") -> str:
    """
    Execute a SELECT query and save the FULL result set as a Markdown table
    to a file. Use this when the user wants to see ALL rows or a large dataset
    (e.g. "show all donations", "list every message from June").

    Unlike execute_sql_query (which caps at 100 rows), this tool runs the query
    unbounded and writes every row to a file. The file path is returned — the
    UI renders the full table inline in the chat, bypassing the LLM context
    limit entirely.
    
    IMPORTANT: DO NOT use this tool if you are also calling generate_static_report 
    or generate_dynamic_report. Choose EXACTLY ONE tool to present data.

    Only SELECT statements are allowed. A safety cap of 5000 rows prevents
    pathological queries.

    Args:
        query: A valid SQLite SELECT statement.
        title: A short human-readable title for the result set
               (e.g. 'All Donations from June').

    Returns:
        The file path, row count, and title — or an error message.
        Example: 'reports/query_2025-06-30_143022.md\\nRows: 150\\nTitle: All Donations from June'
    """
    # Only SELECT queries allowed — this tool runs unbounded.
    if not query.lstrip().upper().startswith("SELECT"):
        return "Error: query_to_inline_table only accepts SELECT statements."

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return "No results found."

        column_names = []
        for description in cursor.description:
            column_names.append(description[0])
        # Convert timestamps from 24-hour ISO to 12-hour display
        rows = _rows_with_display_timestamps(column_names, rows)

        # Safety cap — 5000 rows is enough for any realistic clinic dataset
        # and prevents a runaway query from producing a massive file.
        MAX_ROWS = 5000
        truncated = len(rows) > MAX_ROWS
        rows_to_write = rows[:MAX_ROWS]

        # Build data lines manually
        data_lines = []
        for row in rows_to_write:
            row_str = ""
            for cell in row:
                if row_str:
                    row_str += "\t"
                row_str += str(cell)
            data_lines.append(row_str)
        header = "\t".join(column_names)
        tsv = header + "\n" + "\n".join(data_lines)
        table_md = _tsv_to_markdown_table(tsv)

        # Build the file content with a header and row count.
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        row_note = f"{len(rows)} rows"
        if truncated:
            row_note += f" (showing first {MAX_ROWS})"
        content = (
            f"## {title}\n\n"
            f"*{row_note} \u00b7 {date_str}*\n\n"
            f"{table_md}\n\n"
            f"---\n*Generated by Vetlog AI Assistant*"
        )

        # Save to the reports directory.
        safe_title = title.lower().replace(" ", "_")[:30]
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"query_{timestamp}_{safe_title}.md"
        filepath = os.path.join(REPORTS_DIR, filename)

        with open(filepath, "w") as f:
            f.write(content)

        return f"reports/{filename}\nRows: {len(rows)}\nTitle: {title}"

    except Exception as error:
        return f"Error: {error}"

        connection.close()


@tool
def execute_python_analytics(query: str, python_script: str) -> str:
    """
    Execute a SQLite query and pass the resulting rows to a custom Python script for analysis.

    Use this when you need to parse unstructured text (like extracting names, counting occurrences of irregular patterns, etc.)
    where SQLite's GROUP BY fails and simple Regex isn't enough.

    The tool will:
    1. Run your `query` against the database.
    2. Expose the results to your `python_script` as a list of dictionaries named `rows`.
       Example `rows`: [{"id": 1, "text": "Daisy (Goat) treated"}, {"id": 2, "text": "JDC Foundation donated"}]
    3. Run your script. Any text you `print()` in your script will be returned to you.

    SECURITY: SQL is validated (SELECT-only, raw_messages table only). Python sandbox
    restricts modules and blocks file/network access.

    Args:
        query: The SQL query to fetch the data (e.g. "SELECT text FROM raw_messages WHERE chat_name LIKE '%Donations%'").
        python_script: The Python code to process the `rows` variable. Must use `print()` to output the result.
            Example python_script:
            counts = {}
            for row in rows:
                text = row['text']
                if 'JDC' in text: counts['JDC Foundation'] = counts.get('JDC Foundation', 0) + 1
                elif 'Saylani' in text: counts['Saylani Trust'] = counts.get('Saylani Trust', 0) + 1

            for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"{k}: {v}")
    """
    import io, contextlib

    # Guardrail: Validate SQL before execution
    validation_error = _validate_sql(query)
    if validation_error:
        return validation_error

    # Guardrail: Sanitize Python script before execution
    sanitization_error = _sanitize_python_script(python_script)
    if sanitization_error:
        return sanitization_error

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        fetched_rows = cursor.fetchall()

        # Convert sqlite3.Row to standard dict for the script
        rows = [dict(row) for row in fetched_rows]

        # Build restricted sandbox environment
        import re as _re
        import collections as _collections
        import json as _json
        import math as _math
        import datetime as _datetime
        import itertools as _itertools
        import statistics as _statistics
        import functools as _functools
        import operator as _operator
        import string as _string
        import textwrap as _textwrap
        import typing as _typing
        import decimal as _decimal
        import fractions as _fractions
        import numbers as _numbers
        import hashlib as _hashlib
        import copy as _copy
        import pprint as _pprint
        import csv as _csv

        _output_buffer = []
        def _safe_print(*args, **kwargs):
            _output_buffer.append(" ".join(str(a) for a in args))

        local_env = {
            "rows": rows,
            "re": _re,
            "Counter": _collections.Counter,
            "collections": _collections,
            "json": _json,
            "math": _math,
            "datetime": _datetime,
            "itertools": _itertools,
            "statistics": _statistics,
            "functools": _functools,
            "operator": _operator,
            "string": _string,
            "textwrap": _textwrap,
            "typing": _typing,
            "decimal": _decimal,
            "fractions": _fractions,
            "numbers": _numbers,
            "hashlib": _hashlib,
            "copy": _copy,
            "pprint": _pprint,
            "csv": _csv,
            "print": _safe_print,
        }

        safe_builtins = {}
        import builtins as _builtins
        for name in dir(_builtins):
            if name not in PYTHON_BLOCKED_BUILTINS and not name.startswith("_"):
                safe_builtins[name] = getattr(_builtins, name)
        safe_builtins["__import__"] = _restricted_import
        local_env["__builtins__"] = safe_builtins

        _output_buffer.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                exec(python_script, {}, local_env)
            except Exception as e:
                return f"Python Script Error: {e}"

        output = "\n".join(_output_buffer)
        if not output.strip():
            return "The script executed successfully but printed nothing. Make sure to use print()."

        # Guardrail: Redact credentials from output
        output = _redact_credentials(output)
        return output
    except Exception as e:
        return f"Database Error: {e}"
    finally:
        connection.close()
