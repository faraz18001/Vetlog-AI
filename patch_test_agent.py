import sys
import os

filepath = 'tests/test_agent.py'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Add extract_report_from_messages
report_extractor = """
def extract_report_from_messages(messages) -> str:
    \"\"\"Return the contents of the generated report if applicable.\"\"\"
    for msg in messages:
        if getattr(msg, "type", None) == "tool" and getattr(msg, "name", None) in ("generate_static_report", "generate_dynamic_report"):
            filepath = msg.content
            full_path = os.path.join(ROOT, "app", filepath)
            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    return f.read()
    return ""

# ─────────────────────────────────────────────────────────────────────────────
"""
content = content.replace("# ─────────────────────────────────────────────────────────────────────────────\n# Custom metrics", report_extractor + "# Custom metrics")

# 2. Add ReportSemanticMetric
report_metric = """
class ReportSemanticMetric(BaseMetric):
    \"\"\"Uses Ollama LLM to semantically grade generative reports.\"\"\"
    async_mode: bool = False
    threshold: float = 1.0

    def __init__(self):
        BaseMetric.__init__(self)
        self.score = 0.0
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        meta = test_case.metadata or {}
        gold_report_path = meta.get("gold_report", "")
        
        if not gold_report_path:
            self.score = 1.0
            self.reason = "Not a report test — skipped"
            return self.score

        full_gold_path = os.path.join(ROOT, gold_report_path)
        if not os.path.exists(full_gold_path):
            self.score = 0.0
            self.reason = f"Gold report file missing: {gold_report_path}"
            return self.score

        with open(full_gold_path, "r") as f:
            expected_report = f.read()
            
        actual_report = meta.get("actual_report", "")
        if not actual_report:
            self.score = 0.0
            self.reason = "Agent did not generate a report file."
            return self.score

        from app.agent import get_llm_model
        llm = get_llm_model({"provider": "ollama", "model": "gemma:31b"})

        prompt = f\"\"\"You are an expert evaluator grading an AI agent.
The agent was asked to generate a report based on a database query.

EXPECTED GROUND TRUTH REPORT:
{expected_report}

ACTUAL GENERATED REPORT:
{actual_report}

Your task: Compare the actual generated report to the expected ground truth report.
Ignore minor formatting differences (e.g. Markdown tables vs bulleted lists, slightly different summaries, or date formats).
Focus ONLY on whether the factual data points (numbers, names, events) present in the expected report are accurately reflected in the actual report.

Answer exactly "YES" if all facts match, or "NO" if a fact is missing, hallucinated, or incorrect, followed by a brief reason.
\"\"\"
        try:
            response = llm.invoke(prompt).content
            if response.strip().upper().startswith("YES"):
                self.score = 1.0
                self.reason = "Semantic match: All facts present."
            else:
                self.score = 0.0
                self.reason = f"Semantic mismatch: {response}"
        except Exception as e:
            self.score = 0.0
            self.reason = f"Eval LLM failed: {str(e)}"

        return self.score

    async def a_measure(self, test_case, *args, **kwargs):
        return self.measure(test_case)

    def is_successful(self):
        return self.score >= self.threshold


# ─────────────────────────────────────────────────────────────────────────────
"""
content = content.replace("# ─────────────────────────────────────────────────────────────────────────────\n# pytest-based tests (used by `deepeval test run`)", report_metric + "# pytest-based tests (used by `deepeval test run`)")

# 3. Update run_case_with_tracing try block
old_try = """        agent_sql = extract_sql_from_messages(messages)
        agent_answer = extract_answer_from_messages(messages)
        agent_tool = extract_tool_name_from_messages(messages)
        error = None
    except Exception as e:
        agent_sql = ""
        agent_answer = ""
        error = f"{type(e).__name__}: {str(e)}"
"""
new_try = """        agent_sql = extract_sql_from_messages(messages)
        agent_answer = extract_answer_from_messages(messages)
        agent_tool = extract_tool_name_from_messages(messages)
        actual_report = extract_report_from_messages(messages)
        error = None
    except Exception as e:
        agent_sql = ""
        agent_answer = ""
        agent_tool = ""
        actual_report = ""
        error = f"{type(e).__name__}: {str(e)}"
"""
content = content.replace(old_try, new_try)

# 4. Update run_case_with_tracing metadata
old_meta = """        metadata={
            "agent_sql": agent_sql,
            "agent_tool": agent_tool,
            "expected_tool": case.get("expected_tool", ""),
            "case_id": case["id"],"""
new_meta = """        metadata={
            "agent_sql": agent_sql,
            "agent_tool": agent_tool,
            "actual_report": actual_report,
            "gold_report": case.get("gold_report", ""),
            "expected_tool": case.get("expected_tool", ""),
            "case_id": case["id"],"""
content = content.replace(old_meta, new_meta)

# 5. Update assert_test in test_agent_case
content = content.replace("metrics=[SqlCorrectnessMetric(), HallucinationMetric(), ToolRoutingMetric()]", "metrics=[SqlCorrectnessMetric(), HallucinationMetric(), ToolRoutingMetric(), ReportSemanticMetric()]")

# 6. Update assert_test in main
content = content.replace("metrics=[sql_metric, hal_metric]", "metrics=[sql_metric, hal_metric, ReportSemanticMetric()]")

with open(filepath, 'w') as f:
    f.write(content)
print("tests/test_agent.py patched successfully.")
