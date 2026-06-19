from dotenv import load_dotenv
import os
import sys
import json

from azure.identity import DefaultAzureCredential
from azure.ai.contentunderstanding import ContentUnderstandingClient


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        image_file = 'biz-card-1.png'
        if len(sys.argv) > 1:
            image_file = sys.argv[1]

        load_dotenv()
        endpoint = os.getenv('AI_ENDPOINT')
        analyzer = os.getenv('ANALYZER_NAME')

        client = ContentUnderstandingClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(),
        )

        print(f"Analyzing '{image_file}' with analyzer '{analyzer}'...")

        with open(image_file, "rb") as f:
            image_data = f.read()

        poller = client.begin_analyze_binary(
            analyzer_id=analyzer,
            binary_input=image_data,
        )
        result = poller.result()

        output_file = "results.json"
        with open(output_file, "w") as f:
            json.dump(dict(result), f, indent=4, default=str)
        print(f"Full response saved to {output_file}\n")

        for content in result.contents:
            if hasattr(content, 'fields') and content.fields:
                for field_name, field_data in content.fields.items():
                    value = field_data.value if hasattr(field_data, 'value') else None
                    print(f"{field_name}: {value}")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()
