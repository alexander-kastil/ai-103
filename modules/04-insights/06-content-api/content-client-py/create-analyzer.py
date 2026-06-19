from dotenv import load_dotenv
import os
import json

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentunderstanding import ContentUnderstandingClient


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        endpoint = os.getenv('AI_ENDPOINT')
        analyzer = os.getenv('ANALYZER_NAME')

        with open("biz-card.json", "r") as f:
            analyzer_definition = json.load(f)

        client = ContentUnderstandingClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(),
        )

        print(f"Creating analyzer '{analyzer}'...")
        poller = client.begin_create_analyzer(
            analyzer_id=analyzer,
            resource=analyzer_definition,
            allow_replace=True,
        )
        result = poller.result()
        print(f"Analyzer '{analyzer}' created successfully.")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()
