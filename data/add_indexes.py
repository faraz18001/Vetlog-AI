"""
Add indexes to speed up common agent queries.

Safe to re-run — uses IF NOT EXISTS.

Usage:  python data/add_indexes.py
"""

import sqlite3
import os
import sys


INDEXES = [
    (
        "raw_messages",
        "ix_raw_messages_timestamp",
        "timestamp",
    ),
    (
        "raw_messages",
        "ix_raw_messages_sender",
        "sender",
    ),
    (
        "raw_messages",
        "ix_raw_messages_chat_name",
        "chat_name",
    ),
    (
        "conversation_logs",
        "ix_conversation_logs_thread_user",
        "thread_id, user_id",
    ),
    (
        "conversation_logs",
        "ix_conversation_logs_user_id",
        "user_id",
    ),
]


def main():
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "vetlog.db",
    )

    if not os.path.exists(db_path):
        sys.exit("Database not found at: " + db_path)

    conn = sqlite3.connect(db_path)
    created = 0
    skipped = 0

    for table, name, columns in INDEXES:
        sql = (
            "CREATE INDEX IF NOT EXISTS "
            + name
            + " ON "
            + table
            + "("
            + columns
            + ")"
        )
        cursor = conn.execute(sql)
        if cursor.rowcount == -1:
            created = created + 1
        else:
            skipped = skipped + 1

    conn.commit()
    conn.close()

    print(
        "Done.  created="
        + str(created)
        + "  already-exists="
        + str(skipped)
    )


if __name__ == "__main__":
    main()
