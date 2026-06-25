import json
import os
import sys
import sqlite3
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["PYTHONWARNINGS"] = "ignore"

from app.tools import _get_db_path
from app.agent import initialize_agent

DB_PATH = _get_db_path()

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def execute_gold(sql: str) -> list:
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


def run_test(agent, config, case: dict) -> dict:
    result = {
        "id": case["id"],
        "question": case["question"],
        "difficulty": case["difficulty"],
        "tags": case["tags"],
        "agent_sql": None,
        "agent_tool_result": None,
        "agent_answer": None,
        "agent_raw_messages": [],
        "gold_rows": [],
        "gold_row_count": 0,
        "sql_match": False,
        "hallucination": False,
        "tool_calls_count": 0,
        "error": None,
    }

    # Execute gold SQL
    gold_rows = execute_gold(case["gold_sql"])
    result["gold_rows"] = gold_rows
    result["gold_row_count"] = len(gold_rows)

    if len(gold_rows) == 0:
        result["hallucination_threshold"] = 0
    else:
        result["hallucination_threshold"] = len(gold_rows)

    try:
        seen = 0
        for chunk in agent.stream(
            {"messages": [("user", result["question"])]},
            config=config,
            stream_mode="values",
        ):
            messages = chunk["messages"]
            for msg in messages[seen:]:
                entry = {"type": msg.type, "content": str(msg.content)[:500]}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    entry["tool_calls"] = [
                        {"name": tc["name"], "args": tc["args"]}
                        for tc in msg.tool_calls
                    ]
                    # Capture the SQL the agent generated
                    for tc in msg.tool_calls:
                        if tc["name"] == "execute_sql_query":
                            result["agent_sql"] = tc["args"].get("query")
                result["agent_raw_messages"].append(entry)
                if msg.type == "tool" and hasattr(msg, "content"):
                    result["agent_tool_result"] = msg.content[:500]
                if msg.type == "ai" and not msg.tool_calls:
                    result["agent_answer"] = msg.content[:500]
                if msg.type == "ai" and msg.tool_calls:
                    result["tool_calls_count"] += len(msg.tool_calls)
                seen += 1
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc()

    # Determine SQL match
    if result["agent_sql"]:
        agent_rows = execute_gold(result["agent_sql"])
        if isinstance(agent_rows, list) and len(agent_rows) > 0 and "error" not in agent_rows[0]:
            result["sql_match"] = True
        else:
            result["sql_match"] = False

    # Determine hallucination:
    # If gold has 0 rows but agent claims something happened → hallucination
    # If gold has rows but agent says nothing found → also flagged
    hallucination = False
    if result["gold_row_count"] == 0:
        if result["agent_answer"] and any(
            keyword in result["agent_answer"].lower()
            for keyword in ["yes", "found", "treated", "donated", "checked"]
        ):
            # Agent said something happened when nothing should exist
            hallucination = True
    elif result["gold_row_count"] > 0 and result["agent_answer"]:
        if any(
            keyword in result["agent_answer"].lower()
            for keyword in ["no", "not found", "none", "does not exist", "no data"]
        ):
            # Agent said nothing found when data exists
            hallucination = True

    result["hallucination"] = hallucination

    return result


def generate_report(all_results: list, output_path: str):
    total = len(all_results)
    passed_sql = sum(1 for r in all_results if r["sql_match"] and not r["error"])
    hallucinated = sum(1 for r in all_results if r["hallucination"])
    errors = sum(1 for r in all_results if r["error"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Agent Stress Test Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }}
  h1 {{ color: #333; }}
  .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
  .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex: 1; }}
  .card h2 {{ margin: 0 0 10px; font-size: 14px; color: #666; text-transform: uppercase; }}
  .card .value {{ font-size: 36px; font-weight: bold; }}
  .pass .value {{ color: #22c55e; }}
  .fail .value {{ color: #ef4444; }}
  .warn .value {{ color: #f59e0b; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8f8f8; font-size: 12px; text-transform: uppercase; color: #666; }}
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .badge-pass {{ background: #dcfce7; color: #166534; }}
  .badge-fail {{ background: #fef2f2; color: #991b1b; }}
  .badge-hallucinate {{ background: #fff3cd; color: #856404; }}
  .badge-error {{ background: #f8d7da; color: #721c24; }}
  .detail {{ font-size: 12px; color: #666; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  tr:hover {{ background: #f9f9f9; }}
</style>
</head>
<body>
<h1>🧪 Agent Stress Test Report</h1>
<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<div class="summary">
  <div class="card pass"><h2>SQL Pass Rate</h2><div class="value">{passed_sql}/{total}</div></div>
  <div class="card warn"><h2>Hallucinations</h2><div class="value">{hallucinated}</div></div>
  <div class="card fail"><h2>Errors</h2><div class="value">{errors}</div></div>
  <div class="card"><h2>Total Tests</h2><div class="value">{total}</div></div>
</div>

<table>
<tr>
  <th>ID</th><th>Question</th><th>Difficulty</th><th>SQL</th><th>Hallucination</th><th>Tool Calls</th><th>SQL Agent Generated</th>
</tr>
"""

    for r in all_results:
        sql_badge = "badge-pass" if r["sql_match"] else "badge-fail"
        sql_label = "PASS" if r["sql_match"] else "FAIL"

        if r["hallucination"]:
            hal_badge = "badge-hallucinate"
            hal_label = "⚠️ HALLUCINATED"
        elif r["error"]:
            hal_badge = "badge-error"
            hal_label = "ERROR"
        else:
            hal_badge = "badge-pass"
            hal_label = "CLEAN"

        sqldisplay = (r["agent_sql"] or "-")[:80]

        html += f"""<tr>
  <td><strong>{r['id']}</strong></td>
  <td style="max-width: 300px;">{r['question'][:80]}</td>
  <td>{r['difficulty']}</td>
  <td><span class="badge {sql_badge}">{sql_label}</span></td>
  <td><span class="badge {hal_badge}">{hal_label}</span></td>
  <td>{r['tool_calls_count']}</td>
  <td class="detail">{sqldisplay}</td>
</tr>
<tr style="background: #fafafa;">
  <td colspan="7" style="padding: 4px 16px; font-size: 11px; color: #999;">
    Gold rows: {r['gold_row_count']} | Agent answer: {r.get('agent_answer', '-')[:100]}
    {' | Error: ' + r['error'] if r.get('error') else ''}
  </td>
</tr>
"""

    html += """</table></body></html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"Report written to {output_path}")


def main():
    cases_path = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(cases_path) as f:
        cases = json.load(f)

    print(f"Loading agent...")
    agent = initialize_agent()
    all_results = []
    for i, case in enumerate(cases):
        config = {"configurable": {"thread_id": f"test-{case['id']}-{datetime.now().timestamp()}"}}
        print(f"[{i+1}/{len(cases)}] Testing: {case['id']} — {case['question'][:60]}...")
        result = run_test(agent, config, case)
        status = "✅" if result["sql_match"] and not result["hallucination"] else "❌" if not result["sql_match"] else "⚠️"
        print(f"  {status} SQL={'PASS' if result['sql_match'] else 'FAIL'} Hal={'⚠️' if result['hallucination'] else '✅'} Calls={result['tool_calls_count']}")
        if result.get("agent_sql"):
            print(f"  SQL: {result['agent_sql'][:100]}")
        all_results.append(result)

    report_path = os.path.join(RESULTS_DIR, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    generate_report(all_results, report_path)


if __name__ == "__main__":
    main()
