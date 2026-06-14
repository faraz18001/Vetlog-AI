from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from schemas import IngestionPayload

# 1. Initialize the building
app = FastAPI(title="VetLog EMR API")

# 2. The Bouncer (CORS Middleware)
# Browsers strictly block scripts from sending data to random servers. 
# This tells the browser: "It is okay, I am allowing the Chrome Extension to talk to me."
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows requests from anywhere (we can lock this down later for security)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. The Door (The Endpoint)
@app.post("/webhook/extension")
async def ingest_whatsapp_messages(payload: IngestionPayload):
    # For now, we will just print it to your terminal to prove the connection works.
    # Later, this is where we will route the data into your LangGraph pipeline and SQLite database.
    print(f"🔥 [VETLOG BACKEND] Knock knock! Received {len(payload.messages)} messages from the extension.")
    
    for msg in payload.messages[:3]: # Print just the first 3 so we don't flood the terminal
        print(f"   -> {msg}")
        
    if len(payload.messages) > 3:
        print("   -> ... and more.")

    # 4. The Receipt (The Response sent back to the Chrome Extension)
    return {
        "status": 200, 
        "message": f"Backend successfully caught {len(payload.messages)} messages!"
    }