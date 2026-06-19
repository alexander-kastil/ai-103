from dotenv import load_dotenv
import os

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def main():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')

        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')
        agent_name = os.getenv('AGENT_NAME')

        project_client = AIProjectClient(
            endpoint=foundry_endpoint,
            credential=DefaultAzureCredential(),
        )

        openai_client = project_client.get_openai_client()

        print(f"Connected to agent: {agent_name}")
        print("\nExample prompts:")
        print("  Extract named entities from: 'Pierre and I went to Paris on July 14th.'")
        print("  Identify PII entities and redact them: 'My name is John Smith and my phone is 555-0100.'")
        print("  Analyze sentiment of: 'I booked my flight to Paris in July and it was fantastic!'\n")

        prompt = input("User prompt: ")
        if prompt:
            response = openai_client.responses.create(
                input=[{"role": "user", "content": prompt}],
                extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
            )
            print(f"\n{agent_name}: {response.output_text}")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
