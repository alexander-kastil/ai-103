import os
import time
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


# The same task is solved four ways to compare approaches
TASK = "Classify the sentiment of this customer review: 'The delivery was two days late and the packaging was damaged, but the product itself works great.'"
EXPECTED_KEYWORDS = ["mixed", "positive", "negative", "neutral"]

# --- RAG context simulates retrieved knowledge base content ---
RAG_CONTEXT = """
Sentiment Classification Guidelines:
- Positive: overall satisfaction, praise, recommendation
- Negative: complaints, frustration, dissatisfaction
- Mixed: combination of both positive and negative elements in one review
- Neutral: factual, no clear emotional tone

Examples:
  "Great product, fast shipping" → Positive
  "Broken on arrival, terrible support" → Negative
  "Love the quality but shipping was slow" → Mixed
"""

STRATEGIES = [
    {
        "name": "1. Basic prompt (no system message)",
        "description": "User message only, no guidance.",
        "system": None,
        "user": TASK,
        "temperature": 1.0,
    },
    {
        "name": "2. System message",
        "description": "Adds a role-defining system message.",
        "system": "You are a precise sentiment analysis assistant. Classify text as Positive, Negative, Mixed, or Neutral. Reply with just the label.",
        "user": TASK,
        "temperature": 0.0,
    },
    {
        "name": "3. Few-shot examples",
        "description": "Includes examples in the prompt to guide format.",
        "system": "You are a sentiment analysis assistant.",
        "user": (
            "Examples:\n"
            "  Review: 'Amazing quality!' → Positive\n"
            "  Review: 'Completely broken, waste of money.' → Negative\n"
            "  Review: 'Good product but shipping took forever.' → Mixed\n\n"
            f"Now classify: {TASK}"
        ),
        "temperature": 0.0,
    },
    {
        "name": "4. RAG-grounded prompt",
        "description": "Provides retrieved domain knowledge before the task.",
        "system": "You are a sentiment analysis assistant. Use the provided guidelines to classify sentiment accurately.",
        "user": f"Guidelines:\n{RAG_CONTEXT}\n\nTask: {TASK}\n\nRespond with just the sentiment label.",
        "temperature": 0.0,
    },
]


def run_strategy(openai_client, model_deployment: str, strategy: dict) -> tuple[str, float]:
    messages = []
    if strategy["system"]:
        messages.append({"role": "system", "content": strategy["system"]})
    messages.append({"role": "user", "content": strategy["user"]})

    start = time.time()
    response = openai_client.chat.completions.create(
        model=model_deployment,
        messages=messages,
        max_tokens=60,
        temperature=strategy["temperature"],
    )
    elapsed_ms = (time.time() - start) * 1000

    return response.choices[0].message.content.strip(), elapsed_ms


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

        print("Prompt Optimization — Strategy Comparison Demo")
        print("=" * 55)
        print(f"Task: {TASK}\n")
        print(f"Expected keyword in response: one of {EXPECTED_KEYWORDS}\n")

        results = []

        for strategy in STRATEGIES:
            print(f"Running: {strategy['name']}")
            print(f"  ({strategy['description']})")

            answer, latency_ms = run_strategy(openai_client, model_deployment, strategy)

            matched = any(kw in answer.lower() for kw in EXPECTED_KEYWORDS)
            results.append({
                "name": strategy["name"],
                "answer": answer,
                "latency_ms": latency_ms,
                "matched": matched,
            })

            status = "✓" if matched else "✗"
            print(f"  Response:  {answer}")
            print(f"  Latency:   {latency_ms:.0f}ms")
            print(f"  Keyword:   {status}\n")

        print("=" * 55)
        print("Summary:")
        for r in results:
            status = "PASS" if r["matched"] else "FAIL"
            print(f"  [{status}] {r['name']} — {r['latency_ms']:.0f}ms — \"{r['answer'][:60]}\"")

    except Exception as ex:
        print(f"\nError: {ex}")


if __name__ == '__main__':
    main()
