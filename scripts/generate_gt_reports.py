import os
import shutil
import sqlite3
import pandas as pd
from app.tools import generate_static_report, generate_dynamic_report, _tsv_to_markdown_table

GT_REPORTS_DIR = 'tests/ground_truth_reports'
os.makedirs(GT_REPORTS_DIR, exist_ok=True)

conn = sqlite3.connect('data/vetlog.db')

def fetch_tsv(query):
    df = pd.read_sql_query(query, conn)
    return df.to_csv(sep='\t', index=False)

def move_report(report_path, expected_name):
    # If the tool returned an error string, print it
    if report_path.startswith("Error"):
        print("TOOL ERROR:", report_path)
        return
        
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", report_path)
    dest = os.path.join(GT_REPORTS_DIR, expected_name)
    if os.path.exists(src):
        shutil.move(src, dest)
    else:
        print(f"File not found: {src}")

# 1. Q21: Static donation_ledger for June 3rd, 2026
q21_data = fetch_tsv("SELECT sender, text, timestamp FROM raw_messages WHERE chat_name LIKE '%Donations%' AND timestamp LIKE '2026-06-03%'")
p21 = generate_static_report.func(
    report_type="donation_ledger", 
    title="June 3rd Donations", 
    data=q21_data, 
    summary="Donation ledger for June 3rd, 2026 showing all incoming funds.", 
    date="2026-06-03"
)
move_report(p21, "GT_Q21_donation_ledger.md")

# 2. Q22: Static treatment_log for Daisy
q22_data = fetch_tsv("SELECT sender, text, timestamp FROM raw_messages WHERE chat_name LIKE '%Clinical%' AND text LIKE '%Daisy%'")
p22 = generate_static_report.func(
    report_type="treatment_log",
    title="Daisy (Cat) Treatment Log",
    data=q22_data,
    summary="Complete treatment log for Daisy the Cat, showing 10 visits for wound healing.",
    date="2026-07-31"
)
move_report(p22, "GT_Q22_daisy_treatment.md")

# 3. Q23: Static attendance_sheet for +92 300 1234567
q23_data = fetch_tsv("SELECT sender, text, timestamp FROM raw_messages WHERE chat_name LIKE '%Attendance%' AND sender = '+92 300 1234567'")
p23 = generate_static_report.func(
    report_type="attendance_sheet",
    title="Attendance for +92 300 1234567",
    data=q23_data,
    summary="Attendance sheet showing 50 'Time in' logs for this sender.",
    date="2026-07-31"
)
move_report(p23, "GT_Q23_attendance_sheet.md")

# 4. Q24: Static treatment_log for Parvo
q24_data = fetch_tsv("SELECT sender, text, timestamp FROM raw_messages WHERE chat_name LIKE '%Clinical%' AND text LIKE '%Parvo%'")
p24 = generate_static_report.func(
    report_type="treatment_log",
    title="Parvo Treatment Cases",
    data=q24_data,
    summary="List of all 13 Parvo treatment cases handled by the clinic.",
    date="2026-07-31"
)
move_report(p24, "GT_Q24_parvo_log.md")

# 5. Q25: Static treatment_log for Rabies
q25_data = fetch_tsv("SELECT sender, text, timestamp FROM raw_messages WHERE chat_name LIKE '%Clinical%' AND text LIKE '%rabies%' COLLATE NOCASE")
p25 = generate_static_report.func(
    report_type="treatment_log",
    title="Rabies Vaccine Log",
    data=q25_data,
    summary="Log of all 5 Rabies vaccines administered to various animals.",
    date="2026-07-31"
)
move_report(p25, "GT_Q25_rabies_log.md")

# 6. Q26: Dynamic report for Ms. Fatima
fatima_content = """## Ms. Fatima Donation Summary

Ms. Fatima is our largest individual donor with a total contribution of PKR 450,000 across 3 donations.

### Breakdown:
1. **PKR 200,000**: For shelter rent.
2. **PKR 150,000**: General donation.
3. **PKR 100,000**: For medical supplies.
"""
p26 = generate_dynamic_report.func(
    title="Ms. Fatima Donation Summary",
    content=fatima_content
)
move_report(p26, "GT_Q26_fatima_dynamic.md")

# 7. Q27: Dynamic report for JDC Foundation
jdc_content = """## JDC Foundation Sponsorship

JDC Foundation has contributed a total of PKR 200,000 across two corporate sponsorships.

### Breakdown:
1. **PKR 100,000**: Corporate sponsorship.
2. **PKR 100,000**: Specifically allocated for animal food.
"""
p27 = generate_dynamic_report.func(
    title="JDC Foundation Summary",
    content=jdc_content
)
move_report(p27, "GT_Q27_jdc_dynamic.md")

# 8. Q28: Dynamic report for Anonymous Donors
anon_content = """## Anonymous High-Value Donors

The clinic has received 10 anonymous donations of PKR 50,000 or greater. The amounts vary between PKR 50,000, 60,000, and 75,000. These are critical for sustaining our operations.
"""
p28 = generate_dynamic_report.func(
    title="Anonymous Donors Summary",
    content=anon_content
)
move_report(p28, "GT_Q28_anon_dynamic.md")

# 9. Q29: Static donation_ledger for Blankets
q29_data = fetch_tsv("SELECT sender, text, timestamp FROM raw_messages WHERE chat_name LIKE '%Donations%' AND text LIKE '%blanket%' COLLATE NOCASE")
p29 = generate_static_report.func(
    report_type="donation_ledger",
    title="Blanket Donations",
    data=q29_data,
    summary="Log of the 2 in-kind blanket donations received (from Ali and a local vendor).",
    date="2026-07-31"
)
move_report(p29, "GT_Q29_blankets_ledger.md")

# 10. Q30: Dynamic report for Attendance Irregularities
attendance_content = """## Attendance Irregularities

One staff member (+92 321 9876543) has logged exactly 50 attendance messages citing traffic issues and the need to leave early ("Time in - sorry traffic thi jaldi jana hoga aaj"). Management should review this recurring pattern.
"""
p30 = generate_dynamic_report.func(
    title="Attendance Irregularities",
    content=attendance_content
)
move_report(p30, "GT_Q30_attendance_dynamic.md")

print("Generated 10 Ground Truth reports in tests/ground_truth_reports/")
