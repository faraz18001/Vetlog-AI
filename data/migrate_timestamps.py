"""
Convert existing raw_messages.timestamp values from WhatsApp format to ISO 8601.

WhatsApp formats:
  "9:03 PM, 3/27/2026"       (US: MM/DD/YYYY)
  "5:49 pm, 30/06/2026"      (DD/MM/YYYY)

Target format:  "2026-03-27 21:03:00"  (ISO 8601)

Run once, safe to re-run (skips already-ISO rows).

Usage:  python data/migrate_timestamps.py
"""

import sqlite3
import os
import sys
from datetime import datetime


def _parse_timestamp(ts):
    ts = ts.strip()

    # Already ISO — leave untouched
    if ts.startswith("202"):
        return None  # signal: no change needed

    # US format: "9:03 PM, 3/27/2026"
    try:
        dt = datetime.strptime(ts, "%I:%M %p, %m/%d/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    # DD/MM/YYYY format: "5:49 pm, 30/06/2026"
    try:
        dt = datetime.strptime(ts, "%I:%M %p, %d/%m/%Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    return None  # unrecognised — leave as-is


def main():
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "vetlog.db",
    )

    if not os.path.exists(db_path):
        sys.exit("Database not found at: " + db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, timestamp FROM raw_messages").fetchall()

    updated = 0
    skipped_iso = 0
    skipped_unknown = 0

    for row in rows:
        new_ts = _parse_timestamp(row["timestamp"])
        if new_ts is None:
            if row["timestamp"].startswith("202"):
                skipped_iso = skipped_iso + 1
            else:
                skipped_unknown = skipped_unknown + 1
                print(
                    "SKIP id="
                    + str(row["id"])
                    + "  unrecognised: "
                    + repr(row["timestamp"])
                )
            continue

        conn.execute(
            "UPDATE raw_messages SET timestamp = ? WHERE id = ?",
            (new_ts, row["id"]),
        )
        updated = updated + 1

    conn.commit()
    conn.close()

    print(
        "Done.  updated="
        + str(updated)
        + "  already-iso="
        + str(skipped_iso)
        + "  unrecognised="
        + str(skipped_unknown)
    )


if __name__ == "__main__":
    main()
