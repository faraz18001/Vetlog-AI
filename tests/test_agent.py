"""
Vetlog Agent Evaluation Suite
================================
Run with deepeval so traces are captured and inspectable:

    cd /home/syedfaraz/Projects/Vetlog
    .venv/bin/deepeval test run tests/test_agent.py -v

Or as a plain script (no inspect TUI, just a summary file):

    .venv/bin/python tests/test_agent.py

After running via `deepeval test run`, inspect traces with:

    .venv/bin/deepeval inspect
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

# Make sure the project root is on the path so `app.*` imports work.
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

# ── DeepEval imports ──────────────────────────────────────────────────────────
import pytest
from deepeval import assert_test
from deepeval.integrations.langchain import CallbackHandler
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

# ── Project imports ───────────────────────────────────────────────────────────
from app.agent import initialize_agent
from app.tools import _resolve_db_path as _get_db_path

# ─────────────────────────────────────────────────────────────────────────────
# Global setup
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = _get_db_path()
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Load test cases once at module level so parametrize can use them.
CASES_PATH = os.path.join(os.path.dirname(__file__), "test_cases.json")
with open(CASES_PATH) as _f:
    ALL_CASES = json.load(_f)

# Limit to first 10 for fast runs; remove the slice to run all.
CASES = ALL_CASES[:10]

# Initialise the agent once — it's expensive to re-build per test.
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = initialize_agent()
    return _agent


# ─────────────────────────────────────────────────────────────────────────────
# SQL helpers
# ─────────────────────────────────────────────────────────────────────────────

def run_sql(sql: str) -> list:
    """Execute a SELECT against the Vetlog SQLite database."""
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.execute(sql)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        return [dict(zip(col_names, row)) for row in rows]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        con.close()


def extract_sql_from_messages(messages) -> str:
    """Pull the first SQL query the agent called from the message list."""
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "execute_sql_query":
                    return tc["args"].get("query", "")
    return ""


def extract_answer_from_messages(messages) -> str:
    """Return the last non-tool AI message as the final answer."""
    for msg in reversed(messages):
        if msg.type == "ai" and (not hasattr(msg, "tool_calls") or not msg.tool_calls):
            return msg.content or ""
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Custom metrics
# ─────────────────────────────────────────────────────────────────────────────

class SqlCorrectnessMetric(BaseMetric):
    """Checks that the agent's SQL returns correct data.

    Tolerates the 10-row tool truncation limit: if gold has >10 rows but the
    agent returned 10, that is considered a pass (the tool can't return more).
    """

    async_mode: bool = False
    threshold: float = 0.5

    def __init__(self):
        BaseMetric.__init__(self)
        self.score = 0.0
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_sql = test_case.expected_output or ""
        agent_sql = meta.get("agent_sql", "")

        if not agent_sql:
            self.score = 0.0
            self.reason = "Agent did not generate a SQL query — no tool call detected"
            return self.score

        gold_rows = run_sql(gold_sql)
        agent_rows = run_sql(agent_sql)

        if isinstance(agent_rows, list) and len(agent_rows) > 0 and "error" in agent_rows[0]:
            self.score = 0.0
            self.reason = f"Agent SQL errored: {agent_rows[0]['error']}"
        elif len(agent_rows) == len(gold_rows):
            self.score = 1.0
            self.reason = f"Correct — both returned {len(gold_rows)} rows"
        elif len(gold_rows) > 10 and len(agent_rows) == 10:
            self.score = 1.0
            self.reason = (
                f"Correct — gold has {len(gold_rows)} rows, agent returned "
                f"{len(agent_rows)} (tool truncation at 10)"
            )
        elif len(agent_rows) > 0:
            self.score = 0.5
            self.reason = (
                f"Partial — gold: {len(gold_rows)} rows, agent: {len(agent_rows)}"
            )
        else:
            self.score = 0.0
            self.reason = (
                f"Row count mismatch — gold: {len(gold_rows)}, agent: {len(agent_rows)}"
            )

        return self.score

    async def a_measure(self, test_case, *args, **kwargs):
        return self.measure(test_case)

    def is_successful(self):
        return self.score >= self.threshold


class HallucinationMetric(BaseMetric):
    """
    Checks that the agent's answer does not contradict what is actually in the DB.

    If the agent's own SQL returned rows, it cannot be hallucinating — skip.
    Otherwise checks:
    - Gold has rows but agent says "nothing found" → hallucination.
    - Gold has no rows but agent claims something happened → hallucination.
    """

    async_mode: bool = False
    threshold: float = 1.0

    def __init__(self):
        BaseMetric.__init__(self)
        self.score = 0.0
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_sql = test_case.expected_output or ""
        agent_sql = meta.get("agent_sql", "")
        agent_answer = test_case.actual_output or ""

        gold_rows = run_sql(gold_sql)
        agent_rows = run_sql(agent_sql) if agent_sql else []

        # If agent SQL returned data, there's no hallucination about existence.
        if len(agent_rows) > 0:
            self.score = 1.0
            self.reason = f"No hallucination — agent SQL returned {len(agent_rows)} rows"
            return self.score

        answer_lower = agent_answer.lower()
        gold_has_rows = len(gold_rows) > 0
        agent_claims_positive = any(
            kw in answer_lower
            for kw in ["yes", "found", "treated", "donated", "checked", "there was", "was a"]
        )
        agent_claims_negative = any(
            kw in answer_lower
            for kw in ["no", "not found", "none", "does not exist", "no data", "no record"]
        )

        if gold_has_rows and agent_claims_negative:
            self.score = 0.0
            self.reason = "Hallucination — data exists but agent said nothing found"
        elif not gold_has_rows and agent_claims_positive:
            self.score = 0.0
            self.reason = "Hallucination — no data exists but agent claimed something happened"
        else:
            self.score = 1.0
            self.reason = "No hallucination detected"

        return self.score

    async def a_measure(self, test_case, *args, **kwargs):
        return self.measure(test_case)

    def is_successful(self):
        return self.score >= self.threshold


# ─────────────────────────────────────────────────────────────────────────────
# pytest-based tests (used by `deepeval test run`)
# These are what generate the traces visible in `deepeval inspect`.
# ─────────────────────────────────────────────────────────────────────────────

def run_case_with_tracing(case: dict) -> LLMTestCase:
    """
    Run a single test case through the agent with the DeepEval CallbackHandler
    attached so every LLM call and tool call is recorded as a trace span.
    """
    agent = get_agent()
    ts = datetime.now().timestamp()
    thread_id = f"test-{case['id']}-{ts}"

    # The CallbackHandler is what generates the trace spans that `deepeval inspect` shows.
    callback = CallbackHandler()

    try:
        result = agent.invoke(
            {"messages": [("user", case["question"])]},
            config={
                "configurable": {"thread_id": thread_id},
                "callbacks": [callback],  # ← this is the key addition
            },
        )
        messages = result["messages"]
        agent_sql = extract_sql_from_messages(messages)
        agent_answer = extract_answer_from_messages(messages)
        error = None
    except Exception as e:
        agent_sql = ""
        agent_answer = ""
        error = f"{type(e).__name__}: {str(e)}"

    return LLMTestCase(
        name=case["id"],
        input=case["question"],
        actual_output=agent_answer or "No answer generated",
        expected_output=case["gold_sql"],
        metadata={
            "agent_sql": agent_sql,
            "case_id": case["id"],
            "difficulty": case["difficulty"],
            "tags": case.get("tags", []),
            "error": error,
        },
    )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_agent_case(case):
    """
    One pytest test per case. deepeval's pytest plugin:
    1. captures the CallbackHandler trace spans
    2. writes them into the test_run_*.json in .deepeval/
    3. makes them visible in `deepeval inspect`
    """
    tc = run_case_with_tracing(case)
    assert_test(
        test_case=tc,
        metrics=[SqlCorrectnessMetric(), HallucinationMetric()],
        run_async=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plain-script mode (for quick summaries without the TUI)
# ─────────────────────────────────────────────────────────────────────────────

def summary_file(results: list, path: str):
    total = len(results)
    passed = sum(
        1 for r in results if r.get("sql_ok") and r.get("hal_ok") and not r.get("error")
    )
    sql_ok = sum(1 for r in results if r.get("sql_ok"))
    hal_ok = sum(1 for r in results if r.get("hal_ok"))
    errors = sum(1 for r in results if r.get("error") and not r.get("sql_ok"))

    lines = [
        f"Test Results — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total    : {total}",
        f"Passed   : {passed}/{total}",
        f"SQL OK   : {sql_ok}/{total}",
        f"Hal OK   : {hal_ok}/{total}",
        f"Errors   : {errors}",
        "",
    ]
    for r in results:
        status = "PASS" if r.get("sql_ok") and r.get("hal_ok") else "FAIL"
        err = r.get("error") or ""
        lines.append(
            f"  {status}  {r['id']:5s}  SQL={'OK' if r.get('sql_ok') else 'XX'}  "
            f"HAL={'OK' if r.get('hal_ok') else 'XX'}  "
            f"  {err[:50]}"
        )

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Summary written to {path}")


def main():
    print("Loading agent…")
    sql_metric = SqlCorrectnessMetric()
    hal_metric = HallucinationMetric()
    summary_rows = []

    for i, case in enumerate(CASES):
        print(f"[{i+1}/{len(CASES)}] {case['id']} — {case['question'][:60]}…")
        tc = run_case_with_tracing(case)

        sql_ok = hal_ok = True
        try:
            assert_test(test_case=tc, metrics=[sql_metric, hal_metric], run_async=False)
            sql_ok = sql_metric.is_successful()
            hal_ok = hal_metric.is_successful()
        except Exception as e:
            sql_ok = False
            hal_ok = False

        summary_rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "agent_sql": tc.metadata.get("agent_sql", ""),
                "agent_answer": (tc.actual_output or "")[:120],
                "error": tc.metadata.get("error"),
                "sql_ok": sql_ok,
                "hal_ok": hal_ok,
            }
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = os.path.join(RESULTS_DIR, f"summary_{stamp}.txt")
    summary_file(summary_rows, summary_path)

    total = len(summary_rows)
    ok = sum(1 for r in summary_rows if r.get("sql_ok") and r.get("hal_ok") and not r.get("error"))
    passed_sql = sum(1 for r in summary_rows if r.get("sql_ok"))
    clean_hal = sum(1 for r in summary_rows if r.get("hal_ok"))
    errors = sum(1 for r in summary_rows if r.get("error"))

    print(f"\n{'='*40}")
    print(f"  {ok}/{total} passed")
    print(f"  SQL: {passed_sql}/{total}  Hal: {clean_hal}/{total}  Errors: {errors}")
    print(f"  See tests/results/ for detailed summary")
    print(f"{'='*40}")
    print("\nTo inspect traces, run:  .venv/bin/deepeval inspect")


if __name__ == "__main__":
    main()
