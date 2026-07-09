"""LangSmith custom evaluator for Vetlog agent traces.

Checks agent behaviour for known hallucination patterns:
  1. Donation queries must exclude patient bills and fund allocations.
  2. Patient-count queries must not rely on SQL substring tricks.
  3. Sender lookups must use LIKE, not exact match.

Usage:
    python eval.py --dataset vetlog-eval    # run against a LangSmith dataset
    python eval.py --trace <trace-id>       # evaluate a single trace
"""

import json
import os
import re
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", "")
if not LANGSMITH_API_KEY:
    print("LANGSMITH_API_KEY not set. Skipping LangSmith connection.")
    # Fall back to offline checks


def check_sql_no_bills_in_donation(sql_query: str) -> dict:
    """Ensure donation queries exclude Check-out bills and fund allocations."""
    sql_upper = sql_query.upper()

    has_pkr = "PKR" in sql_upper or "donation" in sql_query.lower()
    if not has_pkr:
        return {"score": None, "reason": "not a donation query"}

    excludes_bills = "CHECK-OUT" not in sql_upper or "NOT LIKE '%CHECK-OUT%'" in sql_upper
    excludes_allocations = "FUNDS ALLOCATED" not in sql_upper or "NOT LIKE '%FUNDS ALLOCATED%'" in sql_upper

    if not excludes_bills:
        return {"score": 0, "reason": "donation query includes patient bills (Check-out)"}
    if not excludes_allocations:
        return {"score": 0, "reason": "donation query includes fund allocations"}

    return {"score": 1, "reason": "donation query correctly excludes bills and allocations"}


def check_sql_no_substring_patient_count(sql_query: str) -> dict:
    """Ensure patient-count queries don't use substr/instr tricks."""
    sql_upper = sql_query.upper()

    has_patient = "PATIENT" in sql_upper or "COUNT(DISTINCT" in sql_upper
    if not has_patient:
        return {"score": None, "reason": "not a patient-count query"}

    uses_substring = "SUBSTR(" in sql_upper or "INSTR(" in sql_upper
    uses_count_distinct_patient = "COUNT(DISTINCT" in sql_upper and "PATIENT" in sql_upper

    if uses_substring and uses_count_distinct_patient:
        return {"score": 0, "reason": "patient-count query uses substring tricks (substr/instr)"}

    return {"score": 1, "reason": "patient query avoids substring tricks"}


def check_sql_uses_like_for_senders(sql_query: str) -> dict:
    """Ensure sender lookups use LIKE, not exact match."""
    sql_upper = sql_query.upper()

    has_sender = "SENDER" in sql_upper
    if not has_sender:
        return {"score": None, "reason": "no sender filter in query"}

    uses_like = "LIKE" in sql_upper
    if not uses_like:
        return {"score": 0, "reason": "sender filter uses exact match instead of LIKE"}
    if "%" not in sql_query:
        return {"score": 0.5, "reason": "sender uses LIKE but without wildcards"}

    return {"score": 1, "reason": "sender filter correctly uses LIKE with wildcards"}


def check_response_avoids_fake_patient_count(response_text: str) -> dict:
    """Ensure the agent doesn't report a precise patient count from substring queries."""
    text_lower = response_text.lower()

    has_number = bool(re.search(r"\b\d+\b", text_lower))
    has_patient_context = any(
        word in text_lower for word in ["patient", "treated", "dr. faraz"]
    )
    admits_uncertainty = any(
        word in text_lower
        for word in ["approximately", "roughly", "more than", "about", "manual", "scan"]
    )

    if not has_patient_context or not has_number:
        return {"score": None, "reason": "not a patient-count response"}

    if not admits_uncertainty:
        return {
            "score": 0,
            "reason": "patient count reported without uncertainty qualifier",
        }

    return {"score": 1, "reason": "patient count includes appropriate uncertainty"}


def check_response_no_bill_as_donation(response_text: str) -> dict:
    """Ensure donation summaries don't mention bills or check-outs."""
    text_lower = response_text.lower()

    is_donation_context = any(
        word in text_lower for word in ["donation", "donated", "donor", "fund drive", "pkr"]
    )
    if not is_donation_context:
        return {"score": None, "reason": "not a donation response"}

    mentions_bill = "check-out" in text_lower or "bill: pkr" in text_lower
    if mentions_bill:
        return {"score": 0, "reason": "donation summary includes patient bills"}

    return {"score": 1, "reason": "donation summary correctly excludes bills"}


def evaluate_sql_queries(trace_messages: list) -> list[dict]:
    """Extract SQL queries from trace messages and run all checks."""
    results = []
    for msg in trace_messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        if "SELECT" not in content.upper():
            continue

        results.append(check_sql_no_bills_in_donation(content))
        results.append(check_sql_no_substring_patient_count(content))
        results.append(check_sql_uses_like_for_senders(content))

    return results


def evaluate_trace(trace: dict) -> dict:
    """Evaluate a full trace and return combined results."""
    messages = trace.get("messages", [])
    response = trace.get("response", "")

    sql_results = evaluate_sql_queries(messages)
    response_results = [
        check_response_avoids_fake_patient_count(response),
        check_response_no_bill_as_donation(response),
    ]

    all_results = sql_results + response_results
    failures = [r for r in all_results if r.get("score") == 0]
    applicable = [r for r in all_results if r.get("score") is not None]

    if not applicable:
        return {"score": 1, "reason": "no applicable checks found", "details": []}

    failed = len(failures)
    total = len(applicable)
    avg_score = sum(r["score"] for r in applicable) / total if total else 1

    return {
        "score": 0 if failed > 0 else 1,
        "reason": f"{failed}/{total} checks failed (avg {avg_score:.2f})",
        "details": [r for r in all_results if r.get("score") is not None],
    }


def evaluate_from_db(thread_id: Optional[str] = None):
    """Evaluate traces stored in the conversation_logs table."""
    import sqlite3

    conn = sqlite3.connect("data/vetlog.db")
    conn.row_factory = sqlite3.Row

    where = ""
    params = ()
    if thread_id:
        where = "WHERE thread_id = ?"
        params = (thread_id,)

    cur = conn.execute(
        f"""
        SELECT thread_id, role, content
        FROM conversation_logs
        {where}
        ORDER BY thread_id, turn_number
        """
    )
    rows = cur.fetchall()
    conn.close()

    threads = {}
    for row in rows:
        tid = row["thread_id"]
        if tid not in threads:
            threads[tid] = {"messages": [], "response": ""}
        if row["role"] == "user":
            threads[tid]["messages"].append({"content": row["content"]})
        else:
            threads[tid]["response"] = row["content"]
            threads[tid]["messages"].append({"content": row["content"]})

    for tid, trace in threads.items():
        result = evaluate_trace(trace)
        status = "PASS" if result["score"] == 1 else "FAIL"
        print(f"\n{'─' * 60}")
        print(f"Thread: {tid}  →  {status}")
        print(f"Reason: {result['reason']}")
        for detail in result["details"]:
            mark = "✓" if detail["score"] == 1 else "✗"
            print(f"  {mark} {detail['reason']}")
        print(f"{'─' * 60}")


# ── LangSmith evaluator hook ──────────────────────────────────────────
def evaluator(run: dict, example: dict) -> dict:
    """LangSmith custom evaluator entry point."""
    outputs = run.get("outputs", {})
    response = ""
    if isinstance(outputs, dict):
        response = outputs.get("response", "")
    elif isinstance(outputs, str):
        response = outputs

    msgs = run.get("inputs", {}).get("messages", [])
    trace = {"messages": msgs, "response": response}
    return evaluate_trace(trace)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vetlog hallucination evaluator")
    parser.add_argument("--thread", type=str, help="Evaluate a single thread_id")
    parser.add_argument("--all", action="store_true", help="Evaluate all threads in DB")
    args = parser.parse_args()

    if args.thread:
        evaluate_from_db(thread_id=args.thread)
    elif args.all:
        evaluate_from_db()
    else:
        print("Use --thread <id> or --all to evaluate traces")
        print("Example: python eval.py --all")
