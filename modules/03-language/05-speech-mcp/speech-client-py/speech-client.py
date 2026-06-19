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
        print("  Synthesize 'Better a witty fool, than a foolish wit!' as speech using voice 'en-GB-SoniaNeural'.")
        print("  Transcribe https://microsoftlearning.github.io/mslearn-ai-language/Labfiles/05-speech-tool/speech_1.wav\n")

        while True:
            prompt = input("User prompt (or 'quit'): ")
            if prompt == "quit" or len(prompt) == 0:
                break

            response = openai_client.responses.create(
                input=[{"role": "user", "content": prompt}],
                extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
            )
            print(f"\n{agent_name}: {response.output_text}\n")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
