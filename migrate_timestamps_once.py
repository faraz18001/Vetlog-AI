"""
One-time migration script.
Converts all existing WhatsApp-format timestamps in raw_messages to ISO-8601.
"""

import sqlite3
from datetime import datetime

DB_PATH = "data/vetlog.db"

def parse_whatsapp_timestamp(ts: str) -> str | None:
    ts = ts.strip()
    
    # EMERGENCY FIX: Reverse the accidental January 7th corruption
    if ts.startswith("2026-01-07 "):
        return ts.replace("2026-01-07 ", "2026-07-01 ")

    try:
        # FIXED: Swapped %m and %d to match DD/MM/YYYY
        dt = datetime.strptime(ts, "%I:%M %p, %d/%m/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None  # Already ISO or unrecognized — skip it

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM raw_messages")
    rows = cursor.fetchall()

    updated = 0
    skipped = 0

    for row_id, ts in rows:
        iso_ts = parse_whatsapp_timestamp(ts)
        if iso_ts is None or iso_ts == ts:
            skipped += 1
            continue
            
        cursor.execute(
            "UPDATE raw_messages SET timestamp = ? WHERE id = ?",
            (iso_ts, row_id)
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"Migration complete: {updated} rows updated, {skipped} rows skipped.")

if __name__ == "__main__":
    migrate()