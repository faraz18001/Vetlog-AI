import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.agent import initialize_agent

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

api_key = os.getenv("OLLAMA_API_KEY", "")
if not api_key:
    print("Warning: OLLAMA_API_KEY is not set. Set it in .env or export it.")
    print("Example: OLLAMA_API_KEY=your_key_here\n")


def main():
    agent = initialize_agent()
    config = {"configurable": {"thread_id": "terminal-session-1"}}

    print("Agent ready. Type your message (or 'exit' to quit).\n")

    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in ("exit", "quit", "q"):
            break

        if not user_input.strip():
            continue

        seen = 0
        for chunk in agent.stream(
            {"messages": [("user", user_input)]},
            config=config,
            stream_mode="values",
        ):
            messages = chunk["messages"]
            for msg in messages[seen:]:
                msg.pretty_print()
                seen += 1
        print()


if __name__ == "__main__":
    main()
