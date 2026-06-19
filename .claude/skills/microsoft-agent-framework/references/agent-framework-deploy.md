# Agent Framework Deployment

## Agent Type Decision

| Agent type | Deployment method |
| --- | --- |
| **Prompt agent** — instructions + model + tools (file search / vector store / MCP), no custom code | `azure-ai-projects` 2.x Python SDK — `project.agents.create_version(PromptAgentDefinition(...))` (see [Prompt Agent Deployment](#prompt-agent-deployment)) |
| **Hosted agent** — your own code, run by Foundry on managed compute | `azd ai agent` (`microsoft.foundry` extension), or the SDK ZIP / container path (see [Hosted Agent Deployment](#hosted-agent-deployment)) |

**Do not default to raw `az rest`.** It hits the same v1 API but makes you hand-manage token scope/refresh, JSON bodies, vector-store ingestion polling, and RBAC. The SDK/azd paths do all of that and are the recommended surfaces. Keep `az rest` for one-off inspection only.

---

## Prompt Agent Deployment

A prompt agent has no container — it runs entirely inside Foundry using a model + instructions + tools. Provision it with the **Microsoft Foundry SDK** (`azure-ai-projects` >= 2.0.0, latest `2.2.0`).

> **2.x is required.** Azure AI Projects 2.x uses the new Foundry projects API and is **incompatible with 1.x**. The 1.x `client.agents.create_agent(...)` call is replaced by `client.agents.create_version(...)` with a typed `PromptAgentDefinition`.

```bash
pip install "azure-ai-projects>=2.0.0" azure-identity
```

### Create a prompt agent (no tools)

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
import os

project = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

agent = project.agents.create_version(
    agent_name="store-ops-helpdesk",
    definition=PromptAgentDefinition(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],   # e.g. gpt-5.4
        instructions=INSTRUCTIONS,                    # module-level string constant
    ),
    description="Store-operations help desk for Contoso Retail.",
)
print(f"{agent.name} version {agent.version}")
```

### Create a prompt agent WITH file-search grounding

The cleanest path for grounding over local documents. `get_openai_client()` handles files + vector stores; `upload_and_poll` blocks until ingestion (parse → chunk → embed) finishes, so the first query is actually grounded.

```python
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
import os

project = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
openai = project.get_openai_client()

# 1. Vector store
vector_store = openai.vector_stores.create(name="store-ops-index")

# 2. Upload each local doc and WAIT for ingestion
assets = Path(__file__).parent / "assets"
for doc in sorted(assets.glob("*.md")):
    with doc.open("rb") as fh:
        openai.vector_stores.files.upload_and_poll(vector_store_id=vector_store.id, file=fh)

# 3. Agent with FileSearchTool attached
agent = project.agents.create_version(
    agent_name="store-ops-helpdesk",
    definition=PromptAgentDefinition(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        instructions=INSTRUCTIONS,
        tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="Store-ops help desk grounded on the operations documents.",
)
```

Query it (grounded response):

```python
conversation = openai.conversations.create()
response = openai.responses.create(
    conversation=conversation.id,
    input="A card reader is declining every card on one lane. What do I do?",
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
print(response.output_text)
```

### File-search limits

- 1 vector store per agent, up to 10,000 files/store, 512 MB/file.
- Default chunking 800 tokens / 400 overlap; embeddings `text-embedding-3-large`.
- **Basic setup** uses Microsoft-managed storage + search (no extra resources). **Standard setup** routes files to your connected Azure Blob + Azure AI Search index — same code.

### Versioning & updates

- Object model is **agent → versions**. The agent `name`, `id`, and endpoint are stable; each `create_version` mints an **immutable** version. Any change (even one prompt edit) = a new version.
- Default routing is **always-latest** (100% traffic → newest). Pin a version via the `version_selector` for production/published agents that need stability.
- Re-running the provisioning script cleanly mints a new version.

### Portal visibility & publishing

A prompt agent created with `create_version` appears immediately in the Foundry portal under **Agents**, has a live endpoint with no separate activation, and is **publishable to Teams / M365** via the portal wizard or the [Agent 365 CLI](agent-365-cli.md). It gets an `instance_identity` automatically (required for publishing).

### RBAC for the provisioning identity

- **Foundry Owner** (formerly Azure AI Owner) on the Foundry resource — to create agents.
- **Storage Blob Data Contributor** on the project storage account — only for Standard setup file upload.

---

## Hosted Agent Deployment

A hosted agent is **your own code**, run by Foundry on Microsoft-managed, per-session VM-isolated sandboxes (scale-to-zero, deprovisioned after ~15 min idle). Ship it as a **ZIP of source** (Foundry builds the image — preview) or a **container image** in ACR. Each agent gets a dedicated Entra agent identity and managed endpoint; containers serve on port **8088** locally.

### Path A — `azd` (recommended)

`azd` packages the source, computes the SHA-256, uploads, polls for `active`, and wires RBAC automatically (including granting the agent identity **Foundry User**).

```bash
azd ext install microsoft.foundry        # one-time: install the Foundry extension (azd 1.25.3+)

# init from a sample manifest (interactive prompts for project/model/region)
azd ai agent init -m "<agent.manifest.yaml URL or path>" --deploy-mode code
cd <agent-folder>

azd provision                            # creates Foundry project, model deployment, App Insights, ACR
azd ai agent run                         # local inner loop — inspector at http://localhost:8088
azd ai agent invoke --local "Hello!"     # invoke the local agent
azd deploy                               # package + push (container) or upload (zip), create the version
azd ai agent invoke "Write a haiku..."   # invoke the deployed agent
azd ai agent monitor --follow            # stream logs
azd down                                 # teardown
```

Non-interactive (CI/CD): `azd ai agent init --no-prompt --project-id "<id>" --deploy-mode code --runtime python_3_13 --entry-point main.py`. With `--no-prompt`, deploy mode defaults to `container`, so pass `--deploy-mode code` explicitly.

Files the template generates: `azure.yaml` (azd service + `startupCommand`), `agent.yaml` (kind, protocols, model, resources, env), `main.py` + `requirements.txt` (or `.csproj` + `Program.cs`), and a Dockerfile for the container path.

### Path B — SDK ZIP (source-code) deploy

Preview; the "modern non-Docker" path. Needs `azure-ai-projects>=2.2.0` and the preview client (`allow_preview=True`). Build a **flat** zip (`main.py` + `requirements.txt` at the root), compute its SHA-256, and create the version:

```python
created = project.beta.agents.create_version_from_code(
    agent_name=AGENT_NAME,
    content=CreateAgentVersionFromCodeContent(
        metadata=CreateAgentVersionFromCodeMetadata(
            definition=HostedAgentDefinition(
                cpu="1", memory="2Gi",
                code_configuration=CodeConfiguration(
                    runtime="python_3_13",
                    entry_point=["python", "main.py"],
                    dependency_resolution="remote_build",   # Foundry installs requirements.txt
                ),
                protocol_versions=[ProtocolVersionRecord(protocol="responses", version="1.0.0")],
                environment_variables={"AZURE_AI_MODEL_DEPLOYMENT_NAME": "gpt-5.4"},
            ),
        ),
        code=(ZIP_PATH.name, code_zip_bytes, "application/zip"),
    ),
    code_zip_sha256=code_zip_sha256,
)
# poll project.agents.get_version(...) until status == "active", then invoke via get_openai_client
```

`dependency_resolution`: `remote_build` (default — small upload, Foundry resolves deps) or `bundled` (ship extracted Linux x86_64 wheels in `packages/`).

### Path C — container via SDK

`azure-ai-projects>=2.1.0`. Build `--platform linux/amd64`, push to ACR, then `project.agents.create_version(agent_name=..., definition=HostedAgentDefinition(container_configuration=ContainerConfiguration(image="...azurecr.io/...:tag"), ...))`. Poll `get_version` → `active`.

The hosting helper packages the sample `main.py` uses: `agent-framework` + `agent-framework-foundry-hosting` (`ResponsesHostServer(agent).run()`).

### Container sizing

Valid CPU/memory pairs (fixed 1:2 ratio): `0.5/1.0Gi`, `1.0/2.0Gi`, `2.0/4.0Gi`, `4.0/8.0Gi`.

### Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `session_creation_failed` / `ModuleNotFoundError` | ZIP wrapped in a folder | Zip contents **flat at root** |
| `bundled` agent fails at runtime | Windows wheels / wrong arch | Ship extracted modules, Linux x86_64 only |
| Image pull fails | Private-endpoint-only ACR | ACR must be reachable over its public endpoint |
| `PermissionDenied` on agents/write | Missing RBAC | Assign **Foundry Project Manager** to deploy; agent identity needs **Foundry User** |
| 401 acquiring token | Wrong scope | Use `--resource https://ai.azure.com` |
| Version stuck `creating` > 10 min (remote_build) | `requirements.txt` resolve failure | Switch to `bundled` |

### Preview / status

Hosted agents and the source-code (ZIP) path are **preview** (`api-version=2025-11-15-preview`; mutating REST calls need header `Foundry-Features: CodeAgents=V1Preview,HostedAgents=V1Preview`). The container path uses `api-version=v1`.
