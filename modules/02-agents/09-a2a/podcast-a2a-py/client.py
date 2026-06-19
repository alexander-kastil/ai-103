""" Client code that connects to the routing agent """

import os
import sys
import asyncio
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

server = os.environ["SERVER_URL"]
port = os.environ["ROUTING_AGENT_PORT"]

def send_prompt(prompt: str):
    url = f"http://{server}:{port}/message"
    payload = {"message": prompt}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json().get("response", "No response from agent.")
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Request failed: {e}"

async def main():
    print("Enter a prompt for the podcast planning agent. Type 'quit' to exit.")
    while True:
        try:
            user_input = input("User [default: Plan a podcast episode about the rise of small language models. I need a catchy title and a segment breakdown.]\n> ")
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        if not user_input:
            user_input = "Plan a podcast episode about the rise of small language models. I need a catchy title and a segment breakdown."
        if user_input.lower() == "quit":
            print("Goodbye!")
            break
        response = send_prompt(user_input)
        print(f"Agent: {response}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
