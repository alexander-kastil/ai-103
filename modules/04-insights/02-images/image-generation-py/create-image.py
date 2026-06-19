import base64
import os
import json

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
import requests


FIXED_PROMPT = "a female whippet dog that enjoys standup paddling with his beloved tall muscular male owner"


def main() -> None:
    # Clear the console for readability when running interactively.
    os.system("cls" if os.name == "nt" else "clear")

    try:
        load_dotenv()
        endpoint = os.getenv("ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")
        api_version = os.getenv("API_VERSION")

        if not endpoint or not model_deployment or not api_version:
            raise ValueError("ENDPOINT, MODEL_DEPLOYMENT, and API_VERSION must be set in .env")

        client = _build_client(endpoint, api_version)

        print(f"Generating with deployment '{model_deployment}' at '{endpoint}' using api_version '{api_version}'...")

        result = client.images.generate(
            model=model_deployment,
            prompt=FIXED_PROMPT,
            n=1,
        )

        json_response = json.loads(result.model_dump_json())
        image_bytes = extract_image_bytes(json_response)

        file_name = "image_1.png"
        save_image(image_bytes, file_name)

    except Exception as ex:  # pragma: no cover - surface any issues to the user
        print(f"Error: {ex}")


def _build_client(endpoint: str, api_version: str) -> AzureOpenAI:
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ),
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
    )


def extract_image_bytes(response_json: dict) -> bytes:
    data = response_json["data"][0]

    if "b64_json" in data and data["b64_json"]:
        return base64.b64decode(data["b64_json"])

    if data.get("url"):
        return requests.get(data["url"]).content

    raise ValueError("Response did not contain a url or b64_json field")


def save_image(image_bytes: bytes, file_name: str) -> None:
    image_dir = os.path.join(os.getcwd(), "images")
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    image_path = os.path.join(image_dir, file_name)
    with open(image_path, "wb") as image_file:
        image_file.write(image_bytes)
    print(f"Image saved as {image_path}")


if __name__ == "__main__":
    main()