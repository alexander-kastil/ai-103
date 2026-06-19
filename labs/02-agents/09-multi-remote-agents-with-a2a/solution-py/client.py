""" Client code that connects to the routing agent """

import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

server = os.environ["SERVER_URL"]
port = os.environ["ROUTING_AGENT_PORT"]

DEFAULT_PROMPT = "Create a title and outline for an article about React programming."

def send_prompt(prompt: str):
    url = f"http://{server}:{port}/message"
    payload = {"message": prompt}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json().get("response", "No response from agent.")
    return f"Error {response.status_code}: {response.text}"

async def main():
    print("Enter a prompt for the agent. Type 'quit' to exit.")
    while True:
        try:
            user_input = input(f"User [default: {DEFAULT_PROMPT}]: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() == "quit":
            print("Goodbye!")
            break
        if not user_input.strip():
            user_input = DEFAULT_PROMPT
        response = send_prompt(user_input)
        print(f"Agent: {response}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
