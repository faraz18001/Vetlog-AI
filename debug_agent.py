import os
import json
from datetime import datetime
from app.agent import initialize_agent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open('tests/test_cases.json', 'r') as f:
    cases = json.load(f)

tq021 = next(c for c in cases if c['id'] == 'TQ-021')

agent = initialize_agent()
ts = datetime.now().timestamp()
res = agent.invoke(
    {"messages": [("user", tq021['question'])]},
    config={"configurable": {"thread_id": f"debug-{ts}"}}
)

for idx, m in enumerate(res["messages"]):
    print(f"--- Msg {idx} ---")
    print(f"Type: {getattr(m, 'type', 'N/A')}")
    print(f"Name: {getattr(m, 'name', 'N/A')}")
    print(f"Tool calls: {getattr(m, 'tool_calls', 'N/A')}")
    print(f"Content: {m.content}")
