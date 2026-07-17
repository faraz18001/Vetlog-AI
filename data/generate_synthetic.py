"""Generate 700+ synthetic messages with mixed English + Roman Urdu."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta
from app.database import engine, RawMessage, Base
from sqlalchemy.orm import Session

SENDERS = ["+92 330 8144305","+92 371 2304510","+92 335 1371933","+92 318 3080006","+92 303 5928250","+92 333 0733505","+92 300 1144550","+92 321 9988776","+92 345 6677889","+92 312 5566778","+92 334 2233445","+92 311 4455667"]
P = ["Rocky","Simba","Oreo","Milo","Luna","Max","Bella","Charlie","Daisy","Cooper","Buddy","Lucy","Leo","Zara","Tiger","Whiskey","Brandy","Misty","Shadow","Bruno","Oscar","Coco","Rex"]
A = ["Dog (Stray)","Cat (Stray)","Dog (Domestic)","Cat (Domestic)","Rabbit","Parrot","Goat","Donkey","Cow","Horse"]
T = ["vaccination","deworming","wound dressing","antibiotic course","fracture cast","skin allergy","parvo","spay","neuter","ear infection","eye treatment","iv fluids","blood test","x-ray","rabies vaccine","distemper vaccine","tick removal","flea treatment","dental cleaning","checkup","bandage change","stitches removal"]
D = ["Al-Khidmat Foundation","Mr. Usman","Dr. Sarah Ahmed","Mrs. Khan","Anonymous Donor","ABC Corporation","Mr. Ali","Community Fund","Rotary Club Lahore","Ms. Fatima","Mr. Rashid","JDC Foundation","Saylani Trust","Local Business Association"]
C = ["stray animal treatment","shelter food","medical supplies","emergency surgery","vaccination drive","spay/neuter program","general fund","winter shelter","rescue operations"]
V = ["Dr. Ahmed","Dr. Faraz","Dr. Sarah","Dr. Hassan"]
MG = ["Ahmad bhai","Ali bhai","@~Ahmad","@~Ali"]
N = ["Abdullah","Faraz","Ali","Sara","Hassan","Ahmed","Usman","Noor","Bilal","Zain"]
DY = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
TM = ["8:30","9:00","9:15","10:00","10:09","10:30","11:00","12:00","13:00","14:00","17:00","17:53","18:00"]
CN = ["stabilized","recovering","critical but stable","minor injury","severe infection","needs surgery"]
RS = ["Normal range","Slightly elevated WBC","All clear","Pending review","Infection detected, starting antibiotics"]
IT = ["50 kg dog food","medical supplies","blankets x20","crates x5","cat food 30 kg","bandages + antiseptic","surgical gloves + masks","cleaning supplies","milk powder"]
INV = ["dog food","cat food","bandages","gloves","medication","cleaning supplies","syringes","iv drips","vaccines"]
EV = ["vaccination drive","shelter cleaning","volunteer orientation","monthly meeting","adoption day","vet camp"]
PL = ["clinic","shelter","vet hospital","rescue center"]

CLINICAL = [
    "Treated {p} ({a}) \u2014 {t}.","{p} ({a}) admitted for {t}. Stable condition.","{p} \u2014 {t} done. Owner ko bata dia hai.","{p} ({a}) discharged after {t}. Recovering well.","Emergency: {p} ({a}) \u2014 {c}. Stabilizing now.","Follow-up: {p} \u2014 recovering well after {t}. Kal dobara check karna hai.","{p} ka blood work agaya. {r}","{p} \u2014 {t} completed. Medicine de di hai.","New patient {p} ({a}) \u2014 {t} today. Uska owner sath hai.","{p} ({a}) ko {t} ki zaroorat thi. Done.","{p} still under observation after {t}. Raat ko check karte raho.","{p} ki condition behtar hai ab. Kal discharge kardenge.","{p} ({a}) needs rebandaging. Abhi kar raha hon.","{p} ({a}) \u2014 {t} + deworming bhi kardi.","{p} ka {t} postponed to tomorrow. Doctor nahi aye.","Bht mushkil case tha {p} ka. {t} karni pari.","{p} ({a}) ko {t} di. 3 din baad follow up.",
]
ATTENDANCE = [
    "Time in {time}","Time out {time}","Time in @ {time} \u2014 clinic shift","Time out {time} \u2014 sab set hai","AJ mujay jaldi jana hai zaroori kaam se @~{mgr}","Me hospital jara hon @~{mgr}","kidhr ho bhai ?","Agaya bhai","Rasta bohat traffic tha. Late hogaya.","{name} time in {time}","{name} time out {time}","Not right now. Thori dair mein free hota.","Bari ha wo weaning pa agai ha.","Morning shift done. Handing over to {name}.","On leave today \u2014 ghar pe emergency hai.","Evening shift cover kar raha hon aj.","{name} absent today \u2014 call kiya tha.","Hospital se wapis agaya. Resuming.","AJ bohat garmi hai. Pani ka intezam karo shelter mein.","Time in {time} \u2014 der se aya, sorry @~{mgr}","Mujay kal ki chutti chahiye @~{mgr}","Time out {time} \u2014 sb patients stable hain.","Kab tak ana hai aj ? @~{name}","Me 10 min mein pohanch raha hon","AJ late hoga, bachay ko school chorna hai","Bhook lage hai, kuch khana mangwalo bhai","Koi mareez hai kya clinic mein abhi ?",
]
DONATION = [
    "Fund update: PKR {amt} collected today. Donor: {donor}.","Donation received \u2014 PKR {amt} from {donor} for {cause}.","In-kind donation: {items} from {donor}. Shelter mein pohanch gaya.","{donor} contributed PKR {amt} for {cause}. Bohat shukriya!","Zakat donation \u2014 PKR {amt} for {cause}. Allocated.","Community fundraiser raised PKR {amt}. Thank you {donor}!","Anonymous donation PKR {amt} for {cause}. Allah barkat de.","Corporate sponsorship \u2014 PKR {amt} from {donor}.","{items} donated by {donor}. {cause} ke liye bohat helpful.","Funds allocated \u2014 PKR {amt} for {cause}.","JDC ne {items} diya. Bohat acha kaam kar rahay hain.","Saylani se call aya tha, wo PKR {amt} ka cheque denge.","PKR {amt} milay {donor} se. {cause} ke liye use karna hai.","Mashallah, PKR {amt} ka donation agaya {donor} se.",
]
ADMIN = [
    "Meeting scheduled for {day} {time} \u2014 sab staff aye.","Inventory: {item} khatam hone wala hai. Reorder karo.","Reminder: {event} coming up on {day}.","{vet} will visit {day} for {purpose}.","New volunteer {name} joining today. Koi orient karega ?","Shelter deep clean on {day}. Sab log help karo.","Transport needed \u2014 {name} ko {place} jana hai {day} ko.","Monthly report due by {day}. Apni reports jama karo.","AC repair done in kennel area. Ab theek hai.","Water pump issue \u2014 plumber bulaya hai. ETA {time}.","Annual vaccinations for shelter animals on {day}.","Group rules ka reminder: professional raho please.","Bijli ka bill agaya hai. PKR 15000. {day} tak jama karna.","Kal ki chutti announce ki jati hai. {day} off.","Naya fridge agaya hai medicine storage ke liye.","Kennel 3 mein leakage hai. Plumber ko batao.","Driver {day} ko available nahi. Koi aur intezam karo.","Rescue call aya tha \u2014 dog accident case near Lahore bridge.","Kal subah 7 baje rescue operation hai. Volunteers chahiye.","Dengue spray karwaya hai clinic mein. Kal tak band rahega.",
]

def fill(tmpl,**kw):
    for k,v in kw.items(): tmpl=tmpl.replace("{"+k+"}",str(v))
    return tmpl

def main():
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    session.query(RawMessage).delete()
    session.commit()

    start=datetime(2026,6,1)
    timestamps=[]
    for d in range(45):
        day=start+timedelta(days=d)
        for _ in range(random.randint(9,24)):
            h,m,s=random.randint(6,23),random.randint(0,59),random.randint(0,59)
            timestamps.append(datetime(day.year,day.month,day.day,h,m,s))
    timestamps.sort()

    rows=[]
    for ts in timestamps:
        iso=ts.strftime("%Y-%m-%d %H:%M:%S")
        sender=random.choice(SENDERS)
        r=random.random()
        if r<0.38: chat="AMG Paws Rescue (Attendance Management Group)"
        elif r<0.62: chat="AMG Paws Rescue (Clinical Group)"
        elif r<0.80: chat="AMG Paws Rescue (Donations/Fundraising)"
        else: chat="AMG Paws Rescue (Admin/Coordination)"
        if "Attendance" in chat: text=fill(random.choice(ATTENDANCE),name=random.choice(N),time=ts.strftime("%H:%M"),mgr=random.choice(MG))
        elif "Clinical" in chat: text=fill(random.choice(CLINICAL),p=random.choice(P),a=random.choice(A),t=random.choice(T),c=random.choice(CN),r=random.choice(RS))
        elif "Donations" in chat: text=fill(random.choice(DONATION),amt=random.choice([1000,2500,5000,7500,10000,15000,20000,25000,30000,50000,100000]),donor=random.choice(D),cause=random.choice(C),items=random.choice(IT))
        else: text=fill(random.choice(ADMIN),name=random.choice(N),day=random.choice(DY),time=random.choice(TM),item=random.choice(INV),event=random.choice(EV),vet=random.choice(V),purpose=random.choice(["checkups","surgeries","training","vaccinations"]),place=random.choice(PL))
        rows.append((chat,sender,text,iso))
    rows.sort(key=lambda r:r[3])

    batch=[]
    for chat,sender,text,iso in rows:
        batch.append(RawMessage(chat_name=chat,sender=sender,text=text,timestamp=iso))
        if len(batch)>=100:
            session.add_all(batch)
            session.commit()
            batch=[]
    if batch:
        session.add_all(batch)
        session.commit()

    count=session.query(RawMessage).count()
    print(f"Generated {count} messages")
    session.close()

if __name__=="__main__": main()
