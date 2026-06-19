"""
Invoke the "Contoso-Job-Application-Triage" workflow from Python.

This script connects to a Microsoft Foundry project, references a workflow that
was published in the Foundry visual designer (see the demo guide in the parent
folder), starts a conversation, streams the run, and prints a tidy summary of
each job application the workflow screened.

The workflow itself does the orchestration server-side: a For-Each loop over a
list of job applications, a Screening-Agent that classifies each application as
Advance / Reject / NeedsReview with a confidence score and structured JSON
output, If/Else routing on confidence and category, and a Response-Agent that
drafts a candidate email for the Advance / NeedsReview paths.
"""

import os
import re
import json

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def print_workflow_output(output_text):
    """Pretty-print the streamed workflow output.

    The Screening-Agent emits a JSON object per application followed by the
    drafted email text (when one was produced). We split the stream into
    (json, trailing-text) pairs and render a readable card for each application.
    """
    applications = re.findall(r"(\{.*?\})(.*?)(?=\{|$)", output_text, re.DOTALL)

    if not applications:
        print(output_text)
        return

    for app_number, (app_json, response_text) in enumerate(applications, start=1):
        try:
            application = json.loads(app_json)
        except json.JSONDecodeError:
            print(app_json)
            print(response_text.strip())
            continue

        category = application.get("decision", application.get("category", "Unknown"))
        confidence = application.get("confidence", 0)
        summary = application.get(
            "applicant_summary", application.get("application_summary", "")
        )

        print("\n" + "=" * 80)
        print(f"Application {app_number}: {category} ({confidence:.0%} confidence)")
        print("-" * 80)
        print(f"Summary: {summary}")
        response_text = response_text.strip()
        if response_text:
            print("\nDrafted candidate email:")
            print(response_text)
    print("=" * 80 + "\n")


def main():
    os.system("cls" if os.name == "nt" else "clear")
    load_dotenv()

    endpoint = os.environ["PROJECT_ENDPOINT"]
    workflow_name = os.getenv("WORKFLOW_NAME", "Contoso-Job-Application-Triage")

    # Connect to the AI Project client and grab the OpenAI-compatible client.
    with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ) as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        # Reference the published workflow by name.
        workflow = {"name": workflow_name}
        print(f"Invoking workflow: {workflow['name']}")

        # Create a conversation and start the workflow run (streamed).
        conversation = openai_client.conversations.create()
        print(f"Created conversation (id: {conversation.id})")

        stream = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={
                "agent_reference": {
                    "name": workflow["name"],
                    "type": "agent_reference",
                }
            },
            input="Start processing job applications",
            stream=True,
        )

        # Process events from the workflow run as they arrive.
        for event in stream:
            if event.type == "response.completed":
                print("\nResponse completed:")
                response = openai_client.responses.retrieve(event.response.id)
                print_workflow_output(response.output_text)

        # Clean up the conversation we created.
        openai_client.conversations.delete(conversation_id=conversation.id)
        print("Conversation deleted")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
