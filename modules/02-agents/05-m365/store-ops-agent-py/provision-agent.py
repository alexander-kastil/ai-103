import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition

load_dotenv(override=True)

ASSETS_DIR = Path(__file__).parent / "assets"
VECTOR_STORE_NAME = "store-ops-index"
AGENT_NAME = "store-ops-assistant"

DOCS = [
    ASSETS_DIR / "pos-troubleshooting.md",
    ASSETS_DIR / "returns-and-refunds-policy.md",
    ASSETS_DIR / "store-opening-closing-checklist.md",
    ASSETS_DIR / "inventory-restock-procedure.md",
]


def build_credential():
    if os.environ.get("MSI_ENDPOINT"):
        return ManagedIdentityCredential()
    return DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
        exclude_shared_token_cache_credential=True,
    )


def load_agent_config():
    with open(ASSETS_DIR / "agent.yaml", "r") as f:
        return yaml.safe_load(f)


def resolve_vector_store(openai_client):
    for vs in openai_client.vector_stores.list():
        if vs.name == VECTOR_STORE_NAME:
            print(f"Reusing existing vector store: {vs.id}")
            return vs

    print(f"Creating vector store '{VECTOR_STORE_NAME}' ...")
    vs = openai_client.vector_stores.create(name=VECTOR_STORE_NAME)
    for doc_path in DOCS:
        with doc_path.open("rb") as fh:
            openai_client.vector_stores.files.upload_and_poll(
                vector_store_id=vs.id, file=fh
            )
        print(f"  Uploaded: {doc_path.name}")
    return vs


def main():
    config = load_agent_config()
    project = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=build_credential(),
    )
    openai_client = project.get_openai_client()

    vector_store = resolve_vector_store(openai_client)

    model = os.environ.get("MODEL_DEPLOYMENT_NAME", config["model"]["deployment_name"])
    instructions = config["instructions"]

    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=model,
            instructions=instructions,
            tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
        ),
        description=config.get("description", ""),
    )

    print(f"Agent:        {agent.name}  (version {agent.version})")
    print(f"Vector store: {vector_store.id}")


if __name__ == "__main__":
    main()
