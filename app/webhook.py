import os
from fastapi import FastAPI, Request
from app.whatsapp_client import WhatsAppClient
from app.openai_client import OpenAIClient

app = FastAPI()

WHATSAPP_HOOK_TOKEN = os.environ.get("WHATSAPP_HOOK_TOKEN")

@app.get("/")
def iam_alive():
    return "Hello World"

@app.get("/webhook/")
def subscribe(request: Request):
    verify_token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    if verify_token == WHATSAPP_HOOK_TOKEN and challenge:
        return int(challenge)

    return "Authentication failed. Invalid token."

@app.post("/webhook/")
async def callback(request: Request):
    print("callback was called...")

    wtsapp_client = WhatsAppClient()

    data = await request.json()
    print(f"Received: {data}")

    response = wtsapp_client.process_notification(data)

    if response.get("statusCode") == 200:
        if response.get("body") and response.get("from_no"):
            openai_client = OpenAIClient()
            reply = openai_client.complete(message=response["body"])
            print(f"\nThe generated response is: {reply}")

            wtsapp_client.send_text_message(
                message=reply,
                phone_number=response["from_no"]
            )
            print(f"\nResponse sent to WhatsApp Cloud: {response}")

    return {"status": "success"}, 200
