import os
import sys
import json
from dotenv import load_dotenv

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "vetlog_eval_reports"

from langsmith import Client
from langsmith.evaluation import evaluate
from langchain_openai import ChatOpenAI
from app.agent import initialize_agent

client = Client()

questions = [
    ("TQ-021", "Generate a static 'donation_ledger' report for all donations received on June 3rd, 2026.", "GT_Q21_donation_ledger.md"),
    ("TQ-022", "Generate a static 'treatment_log' report for Daisy (Cat) containing all her checkups.", "GT_Q22_daisy_treatment.md"),
    ("TQ-023", "Generate a static 'attendance_sheet' report showing all attendance logs for the sender '+92 300 1234567'.", "GT_Q23_attendance_sheet.md"),
    ("TQ-024", "Generate a static 'treatment_log' report for all Parvo treatment cases.", "GT_Q24_parvo_log.md"),
    ("TQ-025", "Generate a static 'treatment_log' report for all Rabies vaccine cases.", "GT_Q25_rabies_log.md"),
    ("TQ-026", "Generate a dynamic report titled 'Ms. Fatima Donation Summary' summarizing all her donations and what they were for.", "GT_Q26_fatima_dynamic.md"),
    ("TQ-027", "Generate a dynamic report titled 'JDC Foundation Summary' summarizing their corporate sponsorships and what they were for.", "GT_Q27_jdc_dynamic.md"),
    ("TQ-028", "Generate a dynamic report titled 'Anonymous Donors Summary' listing all the anonymous donations of PKR 50,000 or greater.", "GT_Q28_anon_dynamic.md"),
    ("TQ-029", "Generate a static 'donation_ledger' report specifically for all blanket donations.", "GT_Q29_blankets_ledger.md"),
    ("TQ-030", "Generate a dynamic report titled 'Attendance Irregularities' highlighting all messages where a sender mentioned 'traffic' or leaving early.", "GT_Q30_attendance_dynamic.md"),
]

dataset_name = "Vetlog Report Generation"

try:
    dataset = client.read_dataset(dataset_name=dataset_name)
    print(f"Dataset '{dataset_name}' already exists.")
except Exception:
    print(f"Creating dataset '{dataset_name}'...")
    dataset = client.create_dataset(dataset_name=dataset_name, description="Evaluates semantic correctness of generated reports.")
    for q_id, q_text, gt_file in questions:
        with open(os.path.join(ROOT, "tests", "ground_truth_reports", gt_file), "r") as f:
            gt_content = f.read()
        client.create_example(
            inputs={"question": q_text},
            outputs={"expected_report": gt_content},
            dataset_id=dataset.id,
            metadata={"case_id": q_id}
        )

# Initialize agent once
agent = initialize_agent()

def predict(inputs: dict) -> dict:
    from datetime import datetime
    thread_id = f"eval-{datetime.now().timestamp()}"
    res = agent.invoke(
        {"messages": [("user", inputs["question"])]},
        config={"configurable": {"thread_id": thread_id}}
    )
    final_msg = res["messages"][-1].content
    
    # Read the generated report locally so LangSmith records the actual text!
    actual_report_content = "No report generated."
    for m in res["messages"]:
        if getattr(m, "type", None) == "tool" and getattr(m, "name", None) in ["generate_static_report", "generate_dynamic_report"]:
            filepath = m.content
            full_path = os.path.join(ROOT, "app", filepath)
            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    actual_report_content = f.read()
                break

    serializable_msgs = []
    for m in res["messages"]:
        d = {"type": m.type, "content": m.content, "name": getattr(m, "name", None)}
        serializable_msgs.append(d)
        
    return {
        "final_message": final_msg, 
        "actual_report": actual_report_content,
        "messages": serializable_msgs
    }

def semantic_evaluator(run, example) -> dict:
    from app.agent import get_llm_model
    llm = get_llm_model({"provider": "ollama", "model": "gemma:31b"})
    
    actual_report_content = run.outputs.get("actual_report", "No report generated.")
    expected_report = example.outputs["expected_report"]
    
    prompt = f"""You are an expert evaluator grading an AI agent.
The agent was asked to generate a report based on a database query.

EXPECTED GROUND TRUTH REPORT:
{expected_report}

ACTUAL GENERATED REPORT:
{actual_report_content}

Your task: Compare the actual generated report to the expected ground truth report.
Ignore minor formatting differences (e.g. Markdown tables vs bulleted lists, slightly different summaries, or date formats).
Focus ONLY on whether the factual data points (numbers, names, events) present in the expected report are accurately reflected in the actual report.

Answer exactly "YES" if all facts match, or "NO" if a fact is missing, hallucinated, or incorrect, followed by a brief reason.
"""
    try:
        response = llm.invoke(prompt).content
        score = 1 if response.strip().upper().startswith("YES") else 0
        return {"key": "Semantic Match", "score": score, "comment": response}
    except Exception as e:
        return {"key": "Semantic Match", "score": 0, "comment": f"Eval failed: {str(e)}"}

if __name__ == "__main__":
    print(f"Starting evaluation on dataset '{dataset_name}'...")
    evaluate(
        predict,
        data=dataset_name,
        evaluators=[semantic_evaluator],
        experiment_prefix="report-eval",
    )
    print("Evaluation complete. View results in LangSmith.")
