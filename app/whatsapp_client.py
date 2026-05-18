import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

PHONE_NUMBER = os.environ.get("PHONE_NUMBER")

class WhatsAppClient:
    API_URL = "https://graph.facebook.com/v15.0/"

    WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
    WHATSAPP_CLOUD_NUMBER_ID = os.environ.get("WHATSAPP_CLOUD_NUMBER_ID")

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        self.API_URL = self.API_URL + str(self.WHATSAPP_CLOUD_NUMBER_ID)

    def send_template_message(self, template_name, language_code, phone_number):
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }

        response = requests.post(
            f"{self.API_URL}/messages",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 200, f"Error sending template message: {response.text}"

        return response.status_code

    def send_text_message(self, message, phone_number):
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }

        response = requests.post(
            f"{self.API_URL}/messages",
            json=payload,
            headers=self.headers
        )

        print(response.status_code)
        print(response.text)

        assert response.status_code == 200, f"Error sending text message: {response.text}"

        return response.status_code

    def process_notification(self, data):
        entries = data.get("entry", [])

        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value")
                if value:
                    if "messages" in value:
                        for message in value["messages"]:
                            if message.get("type") == "text":
                                from_no = message.get("from")
                                message_body = message["text"].get("body")
                                print(f"Ack from FastAPI-WtsApp Webhook: {message_body}")

                                return {
                                    "statusCode": 200,
                                    "body": message_body,
                                    "from_no": from_no,
                                    "isBase64Encoded": False
                                }

        return {
            "statusCode": 403,
            "body": json.dumps("Unsupported method"),
            "isBase64Encoded": False
        }

if __name__ == "__main__":
    client = WhatsAppClient()
    if PHONE_NUMBER:
        response_code = client.send_template_message("hello_world", "en_US", PHONE_NUMBER)
        print(f"Template message response code: {response_code}")
    else:
        print("PHONE_NUMBER not set in environment variables. Check your .env file or Config Vars.")
