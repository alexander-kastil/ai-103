import os
import textwrap

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    PromptAgentDefinitionTextOptions,
    TextResponseFormatJsonSchema,
    WorkflowAgentDefinition,
    FoundryFeaturesOptInKeys,
)

load_dotenv(override=True)

SCREENING_AGENT_NAME = "Screening-Agent"
RESPONSE_AGENT_NAME = "Response-Agent"
WORKFLOW_NAME = "Contoso-Job-Application-Triage"
MODEL = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
ENDPOINT = os.environ["PROJECT_ENDPOINT"]

SCREENING_INSTRUCTIONS = (
    "You are a job-application screener. Classify each application into exactly one of three "
    "decisions: Advance (strong fit, clear evidence of required skills and experience), "
    "Reject (clearly under-qualified or mismatched), or NeedsReview (promising but ambiguous, "
    "missing details, or a borderline call). Provide a confidence score from 0 to 1. "
    "Respond only with the JSON schema provided. Do not discriminate on protected characteristics; "
    "evaluate skills and experience only."
)

RESPONSE_INSTRUCTIONS = (
    "You are a recruiting coordinator. Given a screened job application, draft a short, "
    "professional candidate email. For Advance decisions, invite the candidate to schedule a "
    "first interview and mention one specific strength from their application. For NeedsReview "
    "decisions, request the 1-2 specific missing details a recruiter needs to make a decision. "
    "Keep it under 6 sentences. Tone: warm, professional, inclusive. No emojis."
)

SCREENING_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_summary": {"type": "string"},
        "decision": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "additionalProperties": False,
    "required": ["applicant_summary", "decision", "confidence"],
}

WORKFLOW_YAML = textwrap.dedent(f"""\
    kind: workflow
    trigger:
      kind: OnConversationStart
      id: trigger_wf
      actions:
        - kind: SetVariable
          id: set_job_applications
          variable: Local.JobApplications
          value: |-
            =["Senior Backend Engineer - 8 years Python/Go, led a 6-person team, ex-FAANG, strong system-design portfolio.", "Junior Data Analyst - recent bootcamp grad, no commercial experience, solid SQL exercises, eager to learn.", "Cloud Solutions Architect - 12 years experience but resume is vague on specifics, no certifications listed, gaps unexplained."]
        - kind: Foreach
          id: for_each_application
          items: =Local.JobApplications
          value: Local.CurrentApplication
          actions:
            - kind: InvokeAzureAgent
              id: invoke_screening_agent
              agent:
                name: {SCREENING_AGENT_NAME}
              conversationId: =System.ConversationId
              input:
                messages: =Local.CurrentApplication
              output:
                autoSend: true
                messages: Local.ScreeningOutputText
                responseObject: Local.ScreeningOutputJson
            - kind: ConditionGroup
              id: if_confidence
              conditions:
                - condition: =Local.ScreeningOutputJson.confidence > 0.6
                  id: if_confidence_true
                  actions:
                    - kind: ConditionGroup
                      id: if_decision
                      conditions:
                        - condition: =Local.ScreeningOutputJson.decision = "Reject"
                          id: if_decision_true
                          actions:
                            - kind: SendActivity
                              id: send_rejection
                              activity: Sending a standard rejection notice. No candidate email drafted.
                      elseActions:
                        - kind: InvokeAzureAgent
                          id: invoke_response_agent
                          agent:
                            name: {RESPONSE_AGENT_NAME}
                          conversationId: =System.ConversationId
                          input:
                            messages: =Local.ScreeningOutputText
                          output:
                            autoSend: true
                            messages: Local.ResponseOutputText
              elseActions:
                - kind: SendActivity
                  id: send_human_review
                  activity: |-
                    =Concat("The application screening has low confidence. Routing to a human recruiter for manual review: ", Local.CurrentApplication)
    id: ""
    name: {WORKFLOW_NAME}
    description: ""
""")


def main():
    os.system("cls" if os.name == "nt" else "clear")

    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )

    with AIProjectClient(endpoint=ENDPOINT, credential=credential) as project_client:
        print(f"Connected to: {ENDPOINT}")

        print("\n-- Screening-Agent --")
        screening_def = PromptAgentDefinition(
            model=MODEL,
            instructions=SCREENING_INSTRUCTIONS,
            text=PromptAgentDefinitionTextOptions(
                format=TextResponseFormatJsonSchema(
                    name="screening_response",
                    schema=SCREENING_SCHEMA,
                    strict=True,
                )
            ),
        )
        project_client.agents.create_version(
            SCREENING_AGENT_NAME,
            definition=screening_def,
        )
        print(f"  Published: {SCREENING_AGENT_NAME}")

        print("\n-- Response-Agent --")
        response_def = PromptAgentDefinition(
            model=MODEL,
            instructions=RESPONSE_INSTRUCTIONS,
        )
        project_client.agents.create_version(
            RESPONSE_AGENT_NAME,
            definition=response_def,
        )
        print(f"  Published: {RESPONSE_AGENT_NAME}")

        print("\n-- Contoso-Job-Application-Triage workflow --")
        workflow_def = WorkflowAgentDefinition(
            workflow=WORKFLOW_YAML,
        )
        project_client.agents.create_version(
            WORKFLOW_NAME,
            definition=workflow_def,
            foundry_features=FoundryFeaturesOptInKeys.WORKFLOW_AGENTS_V1_PREVIEW,
            description="Job application triage workflow for the Contoso demo.",
        )
        print(f"  Published: {WORKFLOW_NAME}")

        print("\n-- Listing agents --")
        agents = list(project_client.agents.list())
        for agent in agents:
            marker = " <--" if agent.name == WORKFLOW_NAME else ""
            print(f"  {agent.name}{marker}")

        found = any(a.name == WORKFLOW_NAME for a in agents)
        if found:
            print(f"\nVerification passed: '{WORKFLOW_NAME}' is present in the project.")
        else:
            print(f"\nVerification FAILED: '{WORKFLOW_NAME}' not found in agent listing.")


if __name__ == "__main__":
    main()
