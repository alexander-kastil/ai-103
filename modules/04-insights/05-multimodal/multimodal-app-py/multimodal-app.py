from dotenv import load_dotenv
import os
import time
import json
import requests


CU_VERSION = "2025-05-01-preview"


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        endpoint = os.getenv('ENDPOINT')
        key = os.getenv('KEY')

        # Create analyzers
        print("=== Creating analyzers ===")
        create_analyzer("invoice-analyzer", "invoice-schema.json", endpoint, key)
        create_analyzer("voicemail-analyzer", "voicemail-schema.json", endpoint, key)

        # Analyze an invoice PDF
        print("\n=== Analyzing invoice ===")
        analyze_file("content/invoice-1234.pdf", "invoice-analyzer", "application/pdf", endpoint, key)

        # Analyze a voicemail audio file
        print("\n=== Analyzing voicemail ===")
        analyze_file("content/call-1.mp3", "voicemail-analyzer", "audio/mpeg", endpoint, key)

    except Exception as ex:
        print(ex)


def create_analyzer(analyzer_name, schema_file, endpoint, key):
    print(f"Creating '{analyzer_name}'...")

    with open(schema_file, "r") as f:
        schema = f.read()

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json",
    }
    url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_name}?api-version={CU_VERSION}"

    # Delete if already exists
    requests.delete(url, headers=headers)
    time.sleep(1)

    response = requests.put(url, headers=headers, data=schema)
    if response.status_code not in (200, 201, 202):
        print(f"  Create request failed: {response.status_code} — {response.text}")
        return

    callback_url = response.headers.get("Operation-Location")
    if not callback_url:
        print("  No Operation-Location header — analyzer may already exist.")
        return

    status = "Running"
    while status == "Running":
        time.sleep(2)
        r = requests.get(callback_url, headers=headers)
        status = r.json().get("status", "Unknown")

    if status == "Succeeded":
        print(f"  '{analyzer_name}' ready.")
    else:
        print(f"  Creation ended with status: {status}")
        print(r.json())


def analyze_file(file_path, analyzer_name, content_type, endpoint, key):
    print(f"Submitting '{file_path}'...")

    with open(file_path, "rb") as f:
        data = f.read()

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": content_type,
    }
    url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_name}:analyze?api-version={CU_VERSION}"
    response = requests.post(url, headers=headers, data=data)

    if response.status_code not in (200, 202):
        print(f"  Request failed: {response.status_code} — {response.text}")
        return

    poll_headers = {"Ocp-Apim-Subscription-Key": key}
    result_id = response.json().get("id")
    result_url = f"{endpoint}/contentunderstanding/analyzerResults/{result_id}?api-version={CU_VERSION}"

    status = "Running"
    while status == "Running":
        time.sleep(2)
        r = requests.get(result_url, headers=poll_headers)
        status = r.json().get("status", "Unknown")

    if status != "Succeeded":
        print(f"  Analysis ended with status: {status}")
        return

    result_json = r.json()
    output_file = f"{analyzer_name}-result.json"
    with open(output_file, "w") as f:
        json.dump(result_json, f, indent=4)
    print(f"  Results saved to {output_file}\n")

    contents = result_json.get("result", {}).get("contents", [])
    for content in contents:
        fields = content.get("fields", {})
        for field_name, field_data in fields.items():
            field_type = field_data.get("type")
            if field_type == "string":
                print(f"  {field_name}: {field_data.get('valueString')}")
            elif field_type in ("number", "integer"):
                print(f"  {field_name}: {field_data.get('valueNumber') or field_data.get('valueInteger')}")
            elif field_type == "array":
                items = field_data.get("valueArray", [])
                print(f"  {field_name}: {[i.get('valueString', i) for i in items]}")
            else:
                print(f"  {field_name}: {field_data}")


if __name__ == "__main__":
    main()
