"""
One-time migration script.
Converts WhatsApp-format timestamps in raw_messages to ISO-8601.

Usage:  source .venv/bin/activate && python data/migrate_timestamps.py

The script auto-detects US vs DD/MM locale formats so it works regardless
of which WhatsApp locale was used when the messages were scraped.
"""

import sqlite3
import shutil
from datetime import datetime

DB_PATH = "data/vetlog.db"
BACKUP_PATH = "data/vetlog.db.bak"


def parse_timestamp(ts: str) -> str | None:
    ts = ts.strip()

    # Already ISO or unrecognized — skip
    if ts.startswith("202"):
        return None

    # Try US format: "9:03 PM, 3/27/2026"
    try:
        dt = datetime.strptime(ts, "%I:%M %p, %m/%d/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    # Fallback: DD/MM/YYYY format: "5:49 pm, 30/06/2026"
    try:
        dt = datetime.strptime(ts, "%I:%M %p, %d/%m/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    return None  # Fallthrough — leave as-is


def main():
    # Safety backup
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup saved to {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM raw_messages")
    rows = cursor.fetchall()

    updated = 0
    skipped = 0

    for row_id, ts in rows:
        iso = parse_timestamp(ts)
        if iso is None:
            skipped += 1
            continue

        cursor.execute(
            "UPDATE raw_messages SET timestamp = ? WHERE id = ?",
            (iso, row_id),
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"Migration done: {updated} rows converted to ISO, {skipped} rows skipped.")
    print(f"If anything went wrong, restore from: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
