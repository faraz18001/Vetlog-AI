import os
import sys
from dotenv import load_dotenv

env_path = "/home/syedfaraz/Projects/Vetlog/.env"
load_dotenv(env_path)

os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"

from langsmith import Client

try:
    client = Client()
    thread_id = "3ipavgaq"
    print(f"Fetching runs for thread_id / trace_id containing: {thread_id}")
    
    # Search for runs containing the thread_id in metadata or where trace_id matches
    runs = list(client.list_runs(
        project_name="vetlog",
        execution_order=1 # top level runs
    ))
    
    matched_runs = []
    for r in runs:
        # Check if ID matches, or trace_id matches, or thread_id in metadata
        if thread_id in str(r.id) or thread_id in str(r.trace_id):
            matched_runs.append(r)
        elif r.extra and r.extra.get('metadata', {}).get('thread_id') == thread_id:
            matched_runs.append(r)
            
    print(f"Found {len(matched_runs)} matching top-level runs.")
    
    for r in matched_runs:
        print(f"Run ID: {r.id}, Name: {r.name}, Trace ID: {r.trace_id}")
        
except Exception as e:
    import traceback
    traceback.print_exc()
