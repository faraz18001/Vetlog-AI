import sqlite3
import os
import sys
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import DATABASE_URL
from urllib.parse import urlparse


def _get_db_path() -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parsed = urlparse(DATABASE_URL)
    path = parsed.path
    if path.startswith("/"):
        path = path.lstrip("/")
    resolved = os.path.join(project_root, path) if not os.path.isabs(path) else path
    return resolved or os.path.join(project_root, "vetlog.db")


DB_PATH = _get_db_path()

SENDERS = [
    "Dr. Faraz", "Dr. Sarah Jenkins", "Dr. Ahmed",
    "Nurse Ali", "Nurse Sara", "Receptionist Sara", "Admin Desk",
]

CHAT_CLINICAL = "TEST_Vetlog Clinical Group"
CHAT_ADMIN = "TEST_Vetlog Admin"
CHAT_DONATIONS = "TEST_Vetlog Donations"
CHAT_ATTENDANCE = "TEST_Vetlog Attendance"

ANIMALS = [
    ("Rocky", "Dog (German Shepherd)"),
    ("Max", "Dog (Golden Retriever)"),
    ("Bella", "Dog (Golden Retriever)"),
    ("Charlie", "Dog (Labrador)"),
    ("Lucy", "Cat (Persian)"),
    ("Simba", "Cat (Siamese)"),
    ("Coco", "Parrot"),
    ("Buddy", "Dog (German Shepherd)"),
    ("Daisy", "Cat"),
    ("Oreo", "Rabbit"),
    ("Milo", "Dog (Pomeranian)"),
    ("Tiger", "Cat"),
    ("Shadow", "Dog (Labrador)"),
    ("Luna", "Cat"),
    ("Cooper", "Dog (Beagle)"),
    ("Nala", "Cat"),
    ("Zeus", "Dog (Husky)"),
    ("Chloe", "Cat (Persian)"),
    ("Bailey", "Dog (Labrador)"),
    ("Lola", "Parrot"),
]

ANIMAL_SYNONYMS = {
    "Rocky": ["Rocky", "the GSD", "the German Shepherd", "the big one from Mr. Khan"],
    "Max": ["Max", "the golden one", "the Golden Retriever", "Mr. Ahmed's dog"],
    "Bella": ["Bella", "the spay case", "Mrs. Miller's dog"],
    "Charlie": ["Charlie", "the black Lab", "the Labrador with the limp"],
    "Lucy": ["Lucy", "the white cat", "the Persian"],
    "Simba": ["Simba", "the Siamese", "the orange cat"],
    "Buddy": ["Buddy", "the GSD with the fracture", "the leg fracture case"],
    "Daisy": ["Daisy", "the stray cat", "the calico"],
    "Milo": ["Milo", "the Pomeranian", "the small fluffy one"],
}

DIAGNOSES = [
    "Gastrointestinal Infection", "Ear Infection", "Skin Allergy",
    "Fracture", "Parvo", "Kennel Cough", "Urinary Tract Infection",
    "Dental Disease", "Arthritis", "Eye Infection", "Jaundice",
    "Anemia", "Diabetes", "Kidney Disease", "Heartworm",
]

TREATMENTS = [
    "Vaccination", "Deworming", "Antibiotics course", "Wound dressing",
    "Surgery", "Blood transfusion", "IV fluids", "Eye drops",
    "Ear cleaning", "Dental cleaning", "Flea treatment", "Tick removal",
]

MEDICATIONS = [
    "Amoxicillin", "Metoclopramide", "Carprofen", "Meloxicam",
    "Doxycycline", "Prednisolone", "Fenbendazole", "Praziquantel",
    "Enrofloxacin", "Cephalexin", "Ranitidine", "Omeprazole",
]

OWNERS = [
    "John Smith", "Sarah Miller", "Ahmed Khan", "Fatima Ali",
    "Usman Malik", "Ayesha Gul", "Bilal Hussain", "Zainab Noor",
]

DAILY_MESSAGE_TIME_SLOTS = [
    "8:00 AM", "8:30 AM", "9:00 AM", "9:30 AM", "10:00 AM",
    "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "1:00 PM",
    "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", "4:00 PM",
    "5:00 PM", "6:00 PM", "7:00 PM",
]

DONORS = [
    "Anonymous", "Mr. & Mrs. Khan", "Paws Welfare Trust",
    "Green Pet Foundation", "Al-Khidmat Foundation", "Local Community",
    "Mrs. Fatima", "Mr. Usman",
]


def random_date(start: datetime, end: datetime) -> datetime:
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds()))
    )


def fmt_timestamp(dt: datetime) -> str:
    return dt.strftime("%-I:%M %p, %-m/%-d/%Y")


class Message:
    def __init__(self, chat_name, sender, text, dt):
        self.chat_name = chat_name
        self.sender = sender
        self.text = text
        self.timestamp = fmt_timestamp(dt)
        self.dt = dt


def generate_seed_data() -> list[Message]:
    msgs = []
    now = datetime.now()
    start_date = now - timedelta(days=90)
    rng = random.Random(42)

    # Track patient context for temporal chains
    patient_status = {}  # animal_name -> dict

    # --------------------------------------------
    # 1. Treatment messages (600)
    # --------------------------------------------
    for _ in range(600):
        animal, species = rng.choice(ANIMALS)
        sender = rng.choice(SENDERS)
        dt = random_date(start_date, now)
        chat = rng.choice([CHAT_CLINICAL, CHAT_CLINICAL, CHAT_ADMIN])

        template = rng.choice([
            "Treated {animal} ({species}) — {diagnosis}. {treatment} given.",
            "Administered {medication} to {animal} ({species}). Dosage: {dosage}.",
            "{animal} ({species}) diagnosed with {diagnosis}. Prescribed {medication}.",
            "Follow-up for {animal} ({species}): {diagnosis} is resolving.",
            "{animal} ({species}) brought in with {diagnosis}. {treatment} administered.",
            "Vaccination done for {animal} ({species}) — {diagnosis} prevention.",
            "{animal} is back for {diagnosis}复查. {treatment} repeated.",
            "Emergency case: {animal} ({species}) — {diagnosis}. Stabilized with {medication}.",
        ])
        dosage = f"{rng.randint(1, 3)} tab(s)" if rng.random() < 0.7 else f"{rng.randint(1, 10)} ml"
        text = template.format(
            animal=animal, species=species,
            diagnosis=rng.choice(DIAGNOSES),
            treatment=rng.choice(TREATMENTS),
            medication=rng.choice(MEDICATIONS),
            dosage=dosage,
        )
        msgs.append(Message(chat, sender, text, dt))

    # --------------------------------------------
    # 2. Check-in messages (350)
    # --------------------------------------------
    for _ in range(350):
        animal, species = rng.choice(ANIMALS)
        dt = random_date(start_date, now)
        chat = CHAT_CLINICAL

        template = rng.choice([
            "{animal} ({species}) checked in. Owner: {owner}. Reason: {diagnosis}.",
            "{owner} dropped off {animal} ({species}) for scheduled {treatment}.",
            "Check-in: {animal} ({species}) — {owner} brought him for {diagnosis}.",
            "{animal} arrived at {time}. Owner: {owner}. Appointment for {diagnosis}.",
            "Walk-in: {animal} ({species}) — {owner} says {diagnosis} since yesterday.",
        ])
        text = template.format(
            animal=animal, species=species,
            owner=rng.choice(OWNERS),
            diagnosis=rng.choice(DIAGNOSES),
            treatment=rng.choice(TREATMENTS),
            time=rng.choice(DAILY_MESSAGE_TIME_SLOTS),
        )
        sender = rng.choice(["Receptionist Sara", "Nurse Ali", "Nurse Sara"])
        msgs.append(Message(chat, sender, text, dt))

    # --------------------------------------------
    # 3. Check-out messages (300)
    # --------------------------------------------
    for _ in range(300):
        animal, species = rng.choice(ANIMALS)
        dt = random_date(start_date, now)
        chat = CHAT_CLINICAL

        template = rng.choice([
            "{animal} ({species}) discharged. Owner: {owner}. Status: {status}.",
            "{animal} ready for pickup — {status}. Follow-up in {days} days.",
            "Check-out: {animal} ({species}). {status}. Bill: PKR {bill}.",
            "{animal} going home with {owner}. {status}. Prescribed {medication}.",
            "{animal} discharged after {diagnosis} treatment. {status}.",
        ])
        text = template.format(
            animal=animal, species=species,
            owner=rng.choice(OWNERS),
            diagnosis=rng.choice(DIAGNOSES),
            medication=rng.choice(MEDICATIONS),
            status=rng.choice(["Recovering well", "Stable", "Fully recovered", "Needs monitoring", "Critical but stable"]),
            days=rng.randint(3, 14),
            bill=rng.randint(2000, 25000),
        )
        sender = rng.choice(["Nurse Ali", "Receptionist Sara", "Dr. Faraz", "Dr. Sarah Jenkins"])
        msgs.append(Message(chat, sender, text, dt))

    # --------------------------------------------
    # 4. Attendance messages (350)
    # --------------------------------------------
    shift_types = ["on duty", "signed off", "on call", "half day", "emergency leave"]
    for _ in range(350):
        sender = rng.choice(SENDERS)
        dt = random_date(start_date, now)
        chat = CHAT_ATTENDANCE

        if rng.random() < 0.4:
            text = f"{sender} {rng.choice(shift_types)} {rng.choice(DAILY_MESSAGE_TIME_SLOTS)}."
        elif rng.random() < 0.3:
            covering = rng.choice([s for s in SENDERS if s != sender])
            text = f"{sender} signed off. {covering} covering until {rng.choice(DAILY_MESSAGE_TIME_SLOTS)}."
        elif rng.random() < 0.2:
            text = f"{sender} confirmed appointment schedule for {dt.strftime('%A')}."
        else:
            text = f"Shift handover: {sender} — {rng.randint(3, 12)} cases attended today."
        msgs.append(Message(chat, sender, text, dt))

    # --------------------------------------------
    # 5. Donation messages (250)
    # --------------------------------------------
    for _ in range(250):
        donor = rng.choice(DONORS)
        dt = random_date(start_date, now)
        amount = rng.choice([2000, 5000, 10000, 15000, 25000, 50000])
        chat = CHAT_DONATIONS

        template = rng.choice([
            "Donation received: PKR {amount} from {donor}.",
            "{donor} donated PKR {amount} — designated for {purpose}.",
            "Fund drive update: PKR {amount} collected today. Donor: {donor}.",
            "{donor} contributed PKR {amount} towards {purpose}.",
            "In-kind donation from {donor}: {item}.",
            "{donor} pledged PKR {amount} monthly for {purpose}.",
        ])
        purposes = ["stray animal fund", "surgery costs", "medicine supply", "general clinic fund", "emergency cases"]
        items = ["20kg dog food", "surgical supplies", "blankets", "pet carriers", "medication stock"]
        text = template.format(
            donor=donor, amount=amount,
            purpose=rng.choice(purposes),
            item=rng.choice(items),
        )
        sender = rng.choice(["Admin Desk", "Receptionist Sara", "Dr. Faraz"])
        msgs.append(Message(chat, sender, text, dt))

    # --------------------------------------------
    # 6. Lab result messages (250)
    # --------------------------------------------
    for _ in range(250):
        animal, species = rng.choice(ANIMALS)
        dt = random_date(start_date, now)
        chat = CHAT_CLINICAL

        template = rng.choice([
            "Lab results for {animal} ({species}): {test} — {result}. Normal range: {normal}.",
            "{animal}'s {test} came back: {result}. {interpretation}",
            "Blood work done for {animal} ({species}). Report: {result}",
            "X-ray results for {animal}: {result}. Diagnosis: {diagnosis}.",
            "Fecal test for {animal}: {result}. {treatment} prescribed.",
        ])
        tests = ["CBC", "Blood panel", "Liver enzymes", "Kidney function", "Fecal floatation", "Heartworm test", "X-ray"]
        results_normal = ["within normal limits", "all values normal", "negative", "clear"]
        results_abnormal = ["elevated liver enzymes", "low RBC count", "high WBC count", "positive for parasites", "fracture detected"]
        result = rng.choice(results_normal) if rng.random() < 0.5 else rng.choice(results_abnormal)
        interp = "No action needed." if "normal" in result or "negative" in result or "clear" in result else "Treatment started."

        text = template.format(
            animal=animal, species=species,
            test=rng.choice(tests),
            result=result,
            normal="within reference range",
            interpretation=interp,
            diagnosis=rng.choice(DIAGNOSES),
            treatment=rng.choice(TREATMENTS),
        )
        sender = rng.choice(["Dr. Sarah Jenkins", "Nurse Ali", "Dr. Faraz", "Nurse Sara"])
        msgs.append(Message(chat, sender, text, dt))

    # --------------------------------------------
    # 7. COMPLEX: Temporal chains (50 multi-message sequences)
    # --------------------------------------------
    for chain_id in range(50):
        animal, species = rng.choice(ANIMALS)
        owner = rng.choice(OWNERS)
        diagnosis = rng.choice(DIAGNOSES)
        treatment = rng.choice(TREATMENTS)
        medication = rng.choice(MEDICATIONS)
        base_dt = random_date(start_date, now - timedelta(days=7))

        # Use ANIMAL_SYNONYMS for recurring animals
        synonyms = ANIMAL_SYNONYMS.get(animal, [animal])
        ref = rng.choice(synonyms)

        # Step 1: Check-in (uses different animal reference)
        ref1 = rng.choice(synonyms)
        if ref1 != animal and rng.random() < 0.5:
            t1 = f"{owner} dropped off a {species} — says it has {diagnosis}. No name given yet."
        else:
            t1 = f"{ref1} checked in. Owner: {owner}. Reason: {diagnosis}."
        msgs.append(Message(CHAT_CLINICAL, "Receptionist Sara", t1, base_dt))

        # Step 2: Initial examination (different sender, later time)
        t2_dt = base_dt + timedelta(minutes=rng.randint(15, 60))
        alt_synonyms = [s for s in synonyms if s != ref1]
        ref2 = rng.choice(alt_synonyms) if alt_synonyms else ref1
        t2 = f"Examined {ref2}. Confirmed {diagnosis}. Starting {treatment}."
        msgs.append(Message(CHAT_CLINICAL, "Dr. Faraz", t2, t2_dt))

        # Step 3: Treatment admin (Nurse, later)
        t3_dt = t2_dt + timedelta(minutes=rng.randint(10, 45))
        alt_synonyms2 = [s for s in synonyms if s not in [ref1, ref2]]
        ref3 = rng.choice(alt_synonyms2) if alt_synonyms2 else animal
        t3 = f"Administered {medication} to {ref3}. Dosage: {rng.randint(1, 3)} tab(s)."
        msgs.append(Message(CHAT_CLINICAL, "Nurse Ali", t3, t3_dt))

        # Step 4: Status update (red herring introduced sometimes)
        t4_dt = t3_dt + timedelta(hours=rng.randint(1, 4))
        if rng.random() < 0.2:
            # Red herring — similar animal but different
            other_animal = rng.choice([a for a, _ in ANIMALS if a != animal])
            t4 = f"{other_animal} also being treated for {rng.choice(DIAGNOSES)} — different case."
            msgs.append(Message(CHAT_CLINICAL, rng.choice(["Dr. Sarah Jenkins", "Nurse Sara"]), t4, t4_dt))

        # Step 5: Check-out or follow-up next day
        t5_dt = t4_dt + timedelta(days=rng.randint(0, 2))
        if rng.random() < 0.7:
            t5 = f"{animal} discharged. {rng.choice(['Recovering well', 'Stable', 'Needs follow-up'])}."
            msgs.append(Message(CHAT_CLINICAL, rng.choice(["Nurse Ali", "Dr. Faraz"]), t5, t5_dt))
        else:
            t5 = f"{animal} kept overnight for monitoring. Status: stable."
            msgs.append(Message(CHAT_CLINICAL, "Nurse Sara", t5, t5_dt))

        # Step 6: Follow-up days later (status update that contradicts earlier if not careful)
        t6_dt = t5_dt + timedelta(days=rng.randint(3, 7))
        if rng.random() < 0.15:
            # Contradiction — treatment changed
            t6 = f"{animal} is back — {diagnosis} not resolving. Switching to {rng.choice(MEDICATIONS)}."
        else:
            t6 = f"Follow-up for {animal}: {rng.choice(['Fully recovered', 'Much better', 'Still recovering'])}."
        msgs.append(Message(CHAT_CLINICAL, "Dr. Faraz", t6, t6_dt))

    # --------------------------------------------
    # 8. COMPLEX: Synonym-based messages (150)
    # --------------------------------------------
    for _ in range(150):
        animal, species = rng.choice(ANIMALS)
        synonyms = ANIMAL_SYNONYMS.get(animal, [animal])
        ref = rng.choice(synonyms)
        dt = random_date(start_date, now)
        sender = rng.choice(SENDERS)

        template = rng.choice([
            "Seen {ref} today — {diagnosis} suspected. Running tests.",
            "{ref} needs {treatment}. Owner informed.",
            "Checked on {ref} — {status}.",
            "{ref} is {adjective} today compared to yesterday.",
        ])
        statuses = ["doing much better", "still weak", "eating normally", "temperature is normal", "slightly improved"]
        adjectives = ["more active", "less lethargic", "eating well", "still quiet"]
        text = template.format(
            ref=ref, diagnosis=rng.choice(DIAGNOSES),
            treatment=rng.choice(TREATMENTS),
            status=rng.choice(statuses),
            adjective=rng.choice(adjectives),
        )
        msgs.append(Message(CHAT_CLINICAL, sender, text, dt))

    # --------------------------------------------
    # 9. Attendance + Clinical cross-reference messages (100)
    # --------------------------------------------
    for _ in range(100):
        doctor = rng.choice(["Dr. Faraz", "Dr. Sarah Jenkins", "Dr. Ahmed"])
        dt = random_date(start_date, now)
        time_slot = rng.choice(DAILY_MESSAGE_TIME_SLOTS)

        template = rng.choice([
            "{doctor} on duty {time_slot}. Cases: {count}.",
            "{doctor} requested backup at {time_slot} — emergency case.",
            "{doctor} completed rounds — {count} patients stable.",
            "Reminder: {doctor} scheduled for {time_slot} shift tomorrow.",
        ])
        text = template.format(
            doctor=doctor, time_slot=time_slot, count=rng.randint(3, 12),
        )
        msgs.append(Message(CHAT_ATTENDANCE, "Admin Desk", text, dt))

    # --------------------------------------------
    # 10. Donations cross-referencing animals (100)
    # --------------------------------------------
    for _ in range(100):
        animal, species = rng.choice(ANIMALS)
        donor = rng.choice(DONORS)
        amount = rng.choice([5000, 10000, 15000, 20000])
        dt = random_date(start_date, now)
        chat = CHAT_DONATIONS

        template = rng.choice([
            "Donation of PKR {amount} received — specified for {animal}'s {diagnosis} treatment.",
            "{donor} donated PKR {amount} for {animal} ({species}) — for {diagnosis}.",
            "Funds allocated: PKR {amount} from {donor} towards {animal}'s surgery.",
        ])
        text = template.format(
            animal=animal, species=species, donor=donor,
            amount=amount, diagnosis=rng.choice(DIAGNOSES),
        )
        msgs.append(Message(chat, "Admin Desk", text, dt))

    return msgs


def seed(clear_existing_test_data: bool = True):
    msgs = generate_seed_data()
    msgs.sort(key=lambda m: m.dt)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS raw_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_name VARCHAR NOT NULL,
        sender VARCHAR NOT NULL,
        text TEXT NOT NULL,
        timestamp VARCHAR NOT NULL,
        captured_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    if clear_existing_test_data:
        cur.execute("DELETE FROM raw_messages WHERE chat_name LIKE 'TEST_%'")
        print(f"Cleared existing TEST_ data")

    inserted = 0
    for m in msgs:
        cur.execute(
            "INSERT INTO raw_messages (chat_name, sender, text, timestamp) VALUES (?, ?, ?, ?)",
            (m.chat_name, m.sender, m.text, m.timestamp),
        )
        inserted += 1

    con.commit()
    con.close()
    print(f"Inserted {inserted} seed messages")
    return inserted


if __name__ == "__main__":
    count = seed()
    print(f"Done. Total seeded: {count}")
