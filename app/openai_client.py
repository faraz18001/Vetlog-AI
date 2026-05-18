import os
from openai import OpenAI

class OpenAIClient:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("The 'OPENAI_API_KEY' environment variable is not set.")

        self.client = OpenAI(api_key=api_key)

        print("API key loaded successfully!")

    def complete(self, message: str) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "developer",
                    "content": (
                        "You are a chatbot and should only answer questions related to: "
                        "programming doubts. Politely say you cannot help with other topics."
                    ),
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        response = completion.choices[0].message.content
        print(f"Generated response: {response}")

        return response
