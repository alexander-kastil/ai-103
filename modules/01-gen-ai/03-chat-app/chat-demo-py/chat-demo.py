import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


SYSTEM_MESSAGE = """You are a helpful travel advisor specializing in European destinations.
You provide concise, practical travel tips covering:
- Best times to visit
- Must-see attractions
- Local cuisine recommendations
- Transport advice

Keep responses friendly and focused on the traveller's needs."""

# Few-shot examples that prime the model's tone and format
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "Any tips for visiting Rome?",
    },
    {
        "role": "assistant",
        "content": (
            "Rome is stunning year-round, but spring (April–May) offers mild weather and fewer crowds. "
            "Top must-sees: the Colosseum, Vatican Museums, and Trevi Fountain — book tickets online in advance. "
            "For food, try supplì (fried rice balls) from street vendors and cacio e pepe at a local trattoria. "
            "Use the metro lines A and B to get around quickly."
        ),
    },
]


def build_messages(history: list, user_input: str) -> list:
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]
    messages.extend(FEW_SHOT_EXAMPLES)
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        project_endpoint = os.getenv("PROJECT_CONNECTION")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        project_client = AIProjectClient(
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            ),
            endpoint=project_endpoint,
        )

        openai_client = project_client.get_openai_client(api_version="2024-10-21")

        print("European Travel Advisor — Chat Demo")
        print("=" * 40)
        print("Ask anything about European travel destinations.")
        print("Type 'history' to see the conversation so far.")
        print("Type 'quit' to exit.\n")

        conversation_history = []

        while True:
            user_input = input("You: ").strip()

            if user_input.lower() == "quit":
                print("Goodbye!")
                break
            elif user_input.lower() == "history":
                if not conversation_history:
                    print("(no conversation history yet)\n")
                else:
                    print("\n--- Conversation History ---")
                    for turn in conversation_history:
                        role = "You" if turn["role"] == "user" else "Advisor"
                        print(f"{role}: {turn['content']}\n")
                    print("----------------------------\n")
                continue
            elif not user_input:
                continue

            messages = build_messages(conversation_history, user_input)

            response = openai_client.chat.completions.create(
                model=model_deployment,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )

            reply = response.choices[0].message.content.strip()
            print(f"\nAdvisor: {reply}\n")

            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": reply})

    except Exception as ex:
        print(f"\nError: {ex}")


if __name__ == '__main__':
    main()
