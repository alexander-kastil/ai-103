import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    PromptAgentDefinitionTextOptions,
    TextResponseFormatJsonSchema,
    WorkflowAgentDefinition,
)

ENDPOINT = "https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos"
MODEL = "gpt-5.4"
YAML_PATH = Path(__file__).resolve().parents[1].parent / "modules" / "02-agents" / "06-workflows" / "Contoso-Job-Application-Triage.yaml"

SCREENING_INSTRUCTIONS = (
    "You are a job-application screener. Classify each application into exactly one of three "
    "decisions: Advance (strong fit, clear evidence of required skills and experience), Reject "
    "(clearly under-qualified or mismatched), or NeedsReview (promising but ambiguous, missing "
    "details, or a borderline call). Provide a confidence score from 0 to 1. Respond only with the "
    "JSON schema provided. Do not discriminate on protected characteristics; evaluate skills and "
    "experience only."
)

RESPONSE_INSTRUCTIONS = (
    "You are a recruiting coordinator. Given a screened job application, draft a short, professional "
    "candidate email. For Advance decisions, invite the candidate to schedule a first interview and "
    "mention one specific strength from their application. For NeedsReview decisions, request the 1-2 "
    "specific missing details a recruiter needs to make a decision. Keep it under 6 sentences. Tone: "
    "warm, professional, inclusive. No emojis."
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


def main():
    cred = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    pc = AIProjectClient(endpoint=ENDPOINT, credential=cred)

    existing = {getattr(a, "name", "") for a in pc.agents.list()}

    if "Screening-Agent" not in existing:
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
        s = pc.agents.create_version(agent_name="Screening-Agent", definition=screening_def)
        print("Screening-Agent version:", getattr(s, "version", s))
    else:
        print("Screening-Agent already exists")

    if "Response-Agent" not in existing:
        response_def = PromptAgentDefinition(
            model=MODEL,
            instructions=RESPONSE_INSTRUCTIONS,
        )
        r = pc.agents.create_version(agent_name="Response-Agent", definition=response_def)
        print("Response-Agent version:", getattr(r, "version", r))
    else:
        print("Response-Agent already exists")

    workflow_yaml = YAML_PATH.read_text(encoding="utf-8")
    wf_def = WorkflowAgentDefinition(workflow=workflow_yaml)
    w = pc.agents.create_version(
        agent_name="Contoso-Job-Application-Triage",
        definition=wf_def,
        description="Job-application screening triage workflow (AI-103 module 06 demo).",
        headers={"Foundry-Features": "WorkflowAgents=V1Preview"},
    )
    print("Workflow version:", getattr(w, "version", w))


if __name__ == "__main__":
    main()
