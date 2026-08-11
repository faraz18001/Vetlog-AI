"""
Realistic Vetlog Database Generator
====================================
Generates ~4000 messy WhatsApp messages for a veterinary clinic.
Mixed Roman Urdu + English, typos, duplicates, inconsistent naming.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vetlog.db")

STAFF = {
    "Dr. Faraz": ["Dr. Faraz", "Dr Faraz", "Faraz", "Dr. Faraz Khan"],
    "Dr. Ayesha": ["Dr. Ayesha", "Dr Ayesha", "Ayesha", "Dr. Ayesha Malik"],
    "Nurse Ali": ["Nurse Ali", "Ali", "Ali Bhai", "Nurse Ali Raza"],
    "Receptionist Sara": ["Sara", "Sara Reception", "Sara Khan", "Receptionist Sara"],
    "Dr. Bilal": ["Dr. Bilal", "Dr Bilal", "Bilal"],
    "Nurse Fatima": ["Nurse Fatima", "Fatima", "Fatima Noor"],
    "Dr. Hina": ["Dr. Hina", "Dr Hina", "Hina"],
    "Compounder Kashif": ["Kashif", "Compounder Kashif", "Kashif Bhai"],
    "Cleaner Rahim": ["Rahim", "Rahim Shah", "Cleaner Rahim"],
    "Driver Nasir": ["Nasir", "Driver Nasir", "Nasir Ahmed"],
    "Manager Sana": ["Sana", "Manager Sana", "Sana Iqbal"],
    "Volunteer Hamza": ["Hamza", "Volunteer Hamza", "Hamza Tariq"],
}

ANIMALS = [
    ("Charlie", "dog", "Buddy"), ("Max", "dog", "Ali"), ("Rocky", "dog", "Bilal"),
    ("Bella", "dog", "Sara"), ("Lucy", "dog", "Hina"), ("Cooper", "dog", "Faraz"),
    ("Daisy", "cat", "Ayesha"), ("Luna", "cat", "Sana"), ("Milo", "cat", "Fatima"),
    ("Oliver", "cat", "Kashif"), ("Simba", "cat", "Nasir"), ("Coco", "cat", "Hamza"),
    ("Oreo", "goat", "Rahim"), ("Pepper", "goat", "Ali"), ("Bunny", "rabbit", "Sara"),
    ("Tweety", "bird", "Hina"), ("Kiwi", "bird", "Sana"), ("Shadow", "cat", "Bilal"),
    ("Ginger", "dog", "Ayesha"), ("Patches", "dog", "Fatima"), ("Whiskers", "cat", "Kashif"),
    ("Bruno", "dog", "Hamza"), ("Molly", "dog", "Nasir"), ("Kitty", "cat", "Rahim"),
    ("Dusty", "goat", "Ali"), ("Rosie", "dog", "Sana"), ("Tiger", "cat", "Faraz"),
    ("Lucky", "dog", "Hina"), ("Smokey", "cat", "Bilal"), ("Biscuit", "dog", "Kashif"),
]

CONDITIONS = [
    "parvovirus", "parvo", "Parvo+", "distemper", "kennel cough",
    "skin infection", "fungal", "mange", "rabies", "rabies vaccine",
    "DV2", "deworming", "neuter", "spay", "dental cleaning",
    "fracture", "x-ray", "vomiting", "diarrhea", "jaundice",
    "kidney infection", "ear infection", "eye infection", "abscess",
    "tick fever", "leptospirosis", "giardia", "allergy", "limping",
]

DONORS = [
    "JDC Foundation", "JDC", "JDC foundanon", "Saylani Trust", "Saylani",
    "Edhi Foundation", "Edhi", "Chippa", "Chippa Welfare",
    "Al-Khidmat", "Alkhidmat Foundation", "Shaukat Khanum",
    "Mr. Ahmed", "Ahmed Khan", "Mrs. Saira", "Saira Bano",
    "Anonymous", "anonymous donor", "Gunknown donor", "Walk-in",
    "Mr. Rizwan", "Rizwan Sheikh", "Mrs. Nida", "Nida Parveen",
    "Bilal Enterprises", "Bilal Corp", "Zara Cosmetics", "Zara",
    "Dr. Tariq", "Tariq Mahmood", "Faisal Bank", "HBL donation",
    "Community donation", "Mosque fund", "Zakat", "Sadaqah",
]

DONATION_PURPOSES = [
    "blanket donation", "cash donation", "medicine fund", "general donation",
    "zakat", "sadaqah", "animal feed", "surgery fund", "emergency fund",
    "building fund", "vaccination drive", "rescue operations",
]

EXPENSES = [
    "neem ki dawa", "antibiotic", "vaccine stock", "syringes", "gauze",
    "electricity bill", "gas bill", "rent", "plumbing", "cleaning supplies",
    "cat food", "dog food", "animal feed", "office supplies",
    "neem ki dawa khareed di", "generator repair", "AC repair",
    "staff salary", "internet bill", "water supply",
]


def random_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def pick_name(variants):
    return random.choice(variants)


def generate_clinical(n=1200):
    msgs = []
    start = datetime(2026, 1, 1)
    end = datetime(2026, 8, 10)
    for _ in range(n):
        animal, species, owner = random.choice(ANIMALS)
        doctor = random.choice(list(STAFF.keys()))
        condition = random.choice(CONDITIONS)
        date = random_date(start, end)
        templates = [
            f"{animal} ({species}) ko {condition} hua hai. {pick_name(STAFF[doctor])} ne treat kiya.",
            f"{pick_name(STAFF[doctor])}: {animal} - {condition} +ve. Medicine start.",
            f"Treatment: {animal} ({species}) | Owner: {owner} | Issue: {condition} | Dr: {pick_name(STAFF[doctor])}",
            f"{animal} aaj checkup ke liye aaya. {condition} ke symptoms. {pick_name(STAFF[doctor])} ne dekha.",
            f"URGENT: {animal} ({species}) critical - {condition}. {pick_name(STAFF[doctor])} informed.",
            f"{pick_name(STAFF[doctor])} treated {animal} for {condition}. Follow-up in 3 days.",
            f"{animal} ka {condition} ka injection lagwana hai. Owner {owner} ko bataya.",
        ]
        text = random.choice(templates)
        sender = pick_name(STAFF[doctor])
        msgs.append(("whatsapp - Clinical", sender, text, date.strftime("%Y-%m-%d %H:%M:%S")))
    return msgs


def generate_donations(n=900):
    msgs = []
    start = datetime(2026, 1, 1)
    end = datetime(2026, 8, 10)
    for _ in range(n):
        donor = random.choice(DONORS)
        purpose = random.choice(DONATION_PURPOSES)
        amount = random.choice([500, 1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 25000, 50000, 75000, 100000])
        currency = random.choice(["PKR", "Rs", "rupees", ""])
        date = random_date(start, end)
        templates = [
            f"{donor} ne {amount} {currency} {purpose} diye.",
            f"Donation received: {amount} {currency} from {donor} for {purpose}",
            f"{purpose}: {donor} - PKR {amount}",
            f"{donor}: {amount}Rs diya {purpose} mein. Shukriya!",
            f"JazakAllah {donor} ne {amount} {currency} donate kiye {purpose} ke liye.",
            f"{amount} {currency} {purpose} from {donor}. Receipt generated.",
            f"Alhamdulillah! {donor} ka {amount}Rs donation receive hua - {purpose}",
        ]
        text = random.choice(templates)
        sender = random.choice(["Manager Sana", "Dr. Faraz", "Volunteer Hamza", "Receptionist Sara"])
        sender = pick_name(STAFF[sender])
        msgs.append(("whatsapp - Donations", sender, text, date.strftime("%Y-%m-%d %H:%M:%S")))
    return msgs


def generate_attendance(n=800):
    msgs = []
    start = datetime(2026, 1, 1)
    end = datetime(2026, 8, 10)
    for _ in range(n):
        staff_member = random.choice(list(STAFF.keys()))
        role = random.choice(["on duty", "late", "absent", "leave", "half day", "overtime"])
        date = random_date(start, end)
        templates = [
            f"{pick_name(STAFF[staff_member])} {role} hai aaj.",
            f"{pick_name(STAFF[staff_member])} ne {role} ki request ki hai {date.strftime('%d-%m-%Y')}.",
            f"Aaj {date.strftime('%d/%m/%Y')} ko {pick_name(STAFF[staff_member])} {role}.",
            f"{pick_name(STAFF[staff_member])} {role} - traific ki waja se late mar gaye.",
            f"Attendance: {pick_name(STAFF[staff_member])} | {role} | {date.strftime('%Y-%m-%d')}",
            f"{pick_name(STAFF[staff_member])} nahi aa rahe aaj. Leave maang li hai.",
            f"{pick_name(STAFF[staff_member])} ne bataya ke wo aaj jaldi chala ja raha hai.",
        ]
        text = random.choice(templates)
        sender = random.choice(["Manager Sana", "Receptionist Sara", staff_member])
        sender = pick_name(STAFF[sender])
        msgs.append(("whatsapp - Attendance", sender, text, date.strftime("%Y-%m-%d %H:%M:%S")))
    return msgs


def generate_general(n=600):
    msgs = []
    start = datetime(2026, 1, 1)
    end = datetime(2026, 8, 10)
    topics = [
        ("meeting", ["team meeting kal 3 baje", "monthly meeting hai aaj", "urgent meeting called by manager"]),
        ("rescue", ["stray dog rescue kiya gaya", "3 cats rescue hue gaya billie ke area se", "injured bird aaya rescue se"]),
        ("event", ["free vaccination camp this Saturday", "awareness walk planned", "Eid milad event organize kiya"]),
        ("supplies", ["dog food stock khatam ho raha hai", "vaccine order place ki hai", "new blankets aagaye hai"]),
        ("complaint", ["owner complaint - waiting time zyada", "AC kharab hai clinic mein", "cleanliness issue raised"]),
    ]
    for _ in range(n):
        topic, texts = random.choice(topics)
        text = random.choice(texts)
        date = random_date(start, end)
        sender = pick_name(STAFF[random.choice(list(STAFF.keys()))])
        msgs.append(("whatsapp - General", sender, text, date.strftime("%Y-%m-%d %H:%M:%S")))
    return msgs


def generate_expenses(n=500):
    msgs = []
    start = datetime(2026, 1, 1)
    end = datetime(2026, 8, 10)
    for _ in range(n):
        expense = random.choice(EXPENSES)
        amount = random.choice([1500, 3000, 5000, 8000, 12000, 25000, 50000, 100000])
        date = random_date(start, end)
        templates = [
            f"{expense} ke liye {amount}Rs kharch hue.",
            f"Expense: {expense} | PKR {amount} | approved by manager",
            f"{amount}Rs {expense} par kharch kiye. Receipt attached.",
            f"{expense} ka bill {amount}Rs aaya hai.",
            f"Kharcha: {amount}Rs | {expense} | {date.strftime('%d-%m-%Y')}",
        ]
        text = random.choice(templates)
        sender = random.choice(["Manager Sana", "Compounder Kashif", "Dr. Faraz"])
        sender = pick_name(STAFF[sender])
        msgs.append(("whatsapp - Expenses", sender, text, date.strftime("%Y-%m-%d %H:%M:%S")))
    return msgs


def generate_inventory(n=400):
    msgs = []
    start = datetime(2026, 1, 1)
    end = datetime(2026, 8, 10)
    items = [
        "Rabies vaccine", "DV2 vaccine", "Antibiotic injection", "Deworming tablets",
        "Gauze rolls", "Syringes 5ml", "Cotton pack", "Betadine", "IV drip set",
        "Cat food 10kg", "Dog food 20kg", "Neem shampoo", "Tick spray", "Mange cream",
    ]
    for _ in range(n):
        item = random.choice(items)
        action = random.choice(["restocked", "running low", "finished", "expired", "ordered"])
        qty = random.choice([5, 10, 20, 50, 100])
        date = random_date(start, end)
        templates = [
            f"{item} {action} hai. {qty} units remaining.",
            f"Inventory update: {item} | Status: {action} | Qty: {qty}",
            f"{item} khatam ho gaya hai. Order place karo {qty} units.",
            f"{qty} units {item} {action}.",
        ]
        text = random.choice(templates)
        sender = random.choice(["Compounder Kashif", "Manager Sana", "Nurse Fatima"])
        sender = pick_name(STAFF[sender])
        msgs.append(("whatsapp - Inventory", sender, text, date.strftime("%Y-%m-%d %H:%M:%S")))
    return msgs


def generate_all():
    all_msgs = []
    all_msgs.extend(generate_clinical(1200))
    all_msgs.extend(generate_donations(900))
    all_msgs.extend(generate_attendance(800))
    all_msgs.extend(generate_general(600))
    all_msgs.extend(generate_expenses(500))
    all_msgs.extend(generate_inventory(400))
    random.shuffle(all_msgs)
    return all_msgs


def create_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_name TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            captured_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON raw_messages(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_name ON raw_messages(chat_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sender ON raw_messages(sender)")

    msgs = generate_all()
    cur.executemany(
        "INSERT INTO raw_messages (chat_name, sender, text, timestamp) VALUES (?, ?, ?, ?)",
        msgs
    )

    conn.commit()

    # Stats
    cur.execute("SELECT COUNT(*) FROM raw_messages")
    total = cur.fetchone()[0]
    print(f"Generated {total} messages")

    cur.execute("SELECT chat_name, COUNT(*) FROM raw_messages GROUP BY chat_name")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM raw_messages")
    date_range = cur.fetchone()
    print(f"  Date range: {date_range[0]} to {date_range[1]}")

    conn.close()
    print(f"\nDatabase saved to {DB_PATH}")


if __name__ == "__main__":
    create_database()
