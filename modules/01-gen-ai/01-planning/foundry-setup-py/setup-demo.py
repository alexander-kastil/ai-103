import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        project_endpoint = os.getenv("PROJECT_CONNECTION")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        print("Azure AI Foundry — Project Setup Demo")
        print("=" * 40)

        # Initialize the project client using DefaultAzureCredential
        # This supports az login, managed identity, and environment credentials
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )

        project_client = AIProjectClient(
            credential=credential,
            endpoint=project_endpoint,
        )

        print(f"\nConnected to project endpoint:\n  {project_endpoint}")
        print(f"Model deployment configured: {model_deployment}")

        # Get an OpenAI client scoped to this project
        openai_client = project_client.get_openai_client(api_version="2024-10-21")

        print("\nOpenAI client initialized successfully.")
        print("\nSending a test prompt to verify connectivity...")

        response = openai_client.chat.completions.create(
            model=model_deployment,
            messages=[
                {"role": "system", "content": "You are a concise assistant. Respond in one sentence."},
                {"role": "user", "content": "What is Azure AI Foundry used for?"}
            ],
            max_tokens=100,
        )

        answer = response.choices[0].message.content
        print(f"\nModel response:\n  {answer}")

        print("\n--- Token usage ---")
        print(f"  Prompt tokens:     {response.usage.prompt_tokens}")
        print(f"  Completion tokens: {response.usage.completion_tokens}")
        print(f"  Total tokens:      {response.usage.total_tokens}")

        print("\nSetup complete. Your project is ready for development.")

    except Exception as ex:
        print(f"\nError: {ex}")


if __name__ == '__main__':
    main()
