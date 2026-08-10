import os
import json
from datetime import datetime
from app.agent import initialize_agent

ROOT = os.path.dirname(os.path.abspath(__file__))
print("ROOT:", ROOT)

filepath = "reports/donation_ledger_2026-06-03_june_3,_2026_donation_ledger.md"
filepath = filepath.strip()
full_path = os.path.join(ROOT, "app", filepath)
print("full_path:", full_path)
print("exists:", os.path.exists(full_path))
