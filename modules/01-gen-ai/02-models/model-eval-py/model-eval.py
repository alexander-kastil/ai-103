import os
import time
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


# Reference questions and expected answers for evaluation
EVAL_SET = [
    {
        "question": "What is the capital of France?",
        "expected": "Paris",
    },
    {
        "question": "What programming language is used for data science?",
        "expected": "Python",
    },
    {
        "question": "What does HTTP stand for?",
        "expected": "HyperText Transfer Protocol",
    },
    {
        "question": "What is 15 multiplied by 8?",
        "expected": "120",
    },
]


def contains_expected(response: str, expected: str) -> bool:
    return expected.lower() in response.lower()


def evaluate_model(openai_client, model_deployment: str) -> None:
    print(f"\nEvaluating model: {model_deployment}")
    print("-" * 50)

    correct = 0
    total_latency_ms = 0

    for item in EVAL_SET:
        question = item["question"]
        expected = item["expected"]

        start = time.time()
        response = openai_client.chat.completions.create(
            model=model_deployment,
            messages=[
                {"role": "system", "content": "Answer concisely and directly."},
                {"role": "user", "content": question},
            ],
            max_tokens=50,
            temperature=0,
        )
        elapsed_ms = (time.time() - start) * 1000
        total_latency_ms += elapsed_ms

        answer = response.choices[0].message.content.strip()
        passed = contains_expected(answer, expected)
        if passed:
            correct += 1

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] Q: {question}")
        print(f"        Expected: {expected}")
        print(f"        Got:      {answer}")
        print(f"        Latency:  {elapsed_ms:.0f}ms\n")

    accuracy = (correct / len(EVAL_SET)) * 100
    avg_latency = total_latency_ms / len(EVAL_SET)

    print("=" * 50)
    print(f"Results for {model_deployment}:")
    print(f"  Accuracy:        {accuracy:.1f}%  ({correct}/{len(EVAL_SET)} correct)")
    print(f"  Avg latency:     {avg_latency:.0f}ms")


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        project_endpoint = os.getenv("PROJECT_CONNECTION")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        print("Azure AI Foundry — Model Evaluation Demo")
        print("=" * 50)
        print("This demo runs a small benchmark against a deployed model")
        print("and reports accuracy and latency metrics.\n")

        project_client = AIProjectClient(
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            ),
            endpoint=project_endpoint,
        )

        openai_client = project_client.get_openai_client(api_version="2024-10-21")

        evaluate_model(openai_client, model_deployment)

    except Exception as ex:
        print(f"\nError: {ex}")


if __name__ == '__main__':
    main()
