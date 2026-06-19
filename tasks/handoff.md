# Demo Handoff — modules/02-agents (04 through 09)

Repository: `D:\git-classes\ai-103`
Working directory for all demos: `modules/02-agents/`

All `.env` files, `.gitignore` files, virtual environments, and `requirements.txt` installs are complete for all 6 demos. Code quality fixes (KeyboardInterrupt, CancelledError, default prompts) are applied. The remaining work is Azure resource setup and configuration only.

---

## Credentials (all in `.claude/deploy.config`, git-excluded)

```
PROJECT_ENDPOINT          = https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos
MODEL_DEPLOYMENT_NAME     = gpt-5.4
AZURE_SUBSCRIPTION_ID     = cd091145-5ea2-4703-ba5d-41063b1d4308
AZURE_TENANT_ID           = d92b247e-90e0-4469-a129-6a32866c0d0a
AZURE_AI_SEARCH_ENDPOINT  = https://ai103demossearch.search.windows.net
AZURE_AI_SEARCH_API_KEY   = bMG51uDlhBEtJma0A5TOfQvtNqocV0QHwXs5SY49OVAzSeDvAvG0
```

Foundry account: `ai-103-demos-resource` in resource group `rg-ai-103`, region `swedencentral`.
Foundry project endpoint: `https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos`
Foundry account managed identity principal ID: `aa359067-b96a-48fe-9699-75f7615b082f`

---

## Task 1 — 04-foundry-iq: Create knowledge base and agent

**Demo folder:** `modules/02-agents/04-foundry-iq/fabrikam-audio-py/`
**Script:** `agent_client.py`
**Model:** `gpt-4.1`
**Credential:** `DefaultAzureCredential` (no `az login` needed — browser auth)

### Azure resources already provisioned

| Resource | Name | Endpoint |
|---|---|---|
| AI Search (free, swedencentral) | ai103demossearch | https://ai103demossearch.search.windows.net |
| Storage account | ai103demosstorage | https://ai103demosstorage.blob.core.windows.net/ |
| Blob container | fabrikam-audio | 3 files uploaded: fabrikam-speakers.md, fabrikam-soundbars.md, fabrikam-headphones.md |

RBAC already assigned to Foundry managed identity:
- `Search Index Data Contributor`
- `Search Service Contributor`

`.mcp.json` at repo root is fixed:
- `microsoft-foundry` server pins `mcp>=1.0,<2.0`
- Server reads credentials from `--envFile D:/git-classes/ai-103/.claude/deploy.config`

### What still needs to be done

**Step 1 — Restart session first.**
The `microsoft-foundry` MCP server only loads after a session restart. Once loaded, `mcp__microsoft-foundry__*` tools are available. Check by calling one.

**Step 2 — Create the knowledge base in AI Search.**
Knowledge base name: `kb-fabrikam-audio`
Data source: Azure Blob Storage account `ai103demosstorage`, container `fabrikam-audio`
Storage connection string:
```
DefaultEndpointsProtocol=https;AccountName=ai103demosstorage;AccountKey=<get via: az storage account keys list --account-name ai103demosstorage --resource-group rg-ai-103 --query "[0].value" -o tsv>;EndpointSuffix=core.windows.net
```
Use the `mcp__microsoft-foundry__*` tools to create the index, data source, indexer, and knowledge base. Refer to the mcp-foundry tool list for the exact tool names.

**Step 3 — Create a project connection in Foundry.**
The connection links the Foundry project to the knowledge base MCP endpoint so the agent can call it.
Connection type: `RemoteTool`
Authentication: `ProjectManagedIdentity`
Target: the knowledge base MCP endpoint on the AI Search service

**Step 4 — Create the agent in Foundry.**
Agent name: `fabrikam-audio-agent`
Model: `gpt-4.1`
System prompt (exact):
```
You are a helpful AI assistant for Fabrikam Audio, specializing in home-audio and
home-theater products such as speakers, soundbars, and headphones. You must ALWAYS
search the knowledge base to answer questions about our products or product catalog.
Provide detailed, accurate information and always cite your sources. If you don't find
relevant information in the knowledge base, say so clearly.
```
Tool: attach the `kb-fabrikam-audio` knowledge base as an MCP tool.
Approval: set tool approval to "Ask for approval for all tools" (do this in VS Code Foundry Toolkit extension — the portal doesn't expose this toggle yet).

**Step 5 — Verify.**
Run the Python client:
```powershell
cd modules\02-agents\04-foundry-iq\fabrikam-audio-py
.venv\Scripts\Activate.ps1
python agent_client.py
```
Send: `What types of products does Fabrikam Audio offer?`
An MCP approval prompt should appear. Type `yes`. Agent should respond with product info citing the Fabrikam Audio catalog files.

**Reference files:**
- Demo readme (full portal walkthrough, steps 1–11): `modules/02-agents/04-foundry-iq/readme.md`
- Provision script (already run, idempotent): `modules/02-agents/04-foundry-iq/provision.azcli`
- Deprovision script: `modules/02-agents/04-foundry-iq/deprovision.azcli`
- Client script: `modules/02-agents/04-foundry-iq/fabrikam-audio-py/agent_client.py`
- `.env`: `modules/02-agents/04-foundry-iq/fabrikam-audio-py/.env`

---

## Task 2 — 05-m365: Verify Work IQ setup

**Demo folder:** `modules/02-agents/05-m365/store-ops-workiq-py/`
**Script:** `workiq_demo.py`
**Model:** `gpt-4.1`
**Credential:** `DefaultAzureCredential`

### Blockers

1. Work IQ npm package must be installed globally:
   ```bash
   npm install -g @microsoft/workiq
   workiq accept-eula
   ```
2. M365 Copilot license required on the Azure tenant (`d92b247e-90e0-4469-a129-6a32866c0d0a`).
3. Admin consent in Entra ID may be required for the Work IQ MCP server scopes.

### What to do

1. Check if `workiq` is already installed: `workiq --version`
2. If not, install it (requires npm).
3. Check if M365 Copilot license exists on the tenant. If not, this demo cannot run — mark it blocked in `state.md` and move on.
4. If license exists, run the script and confirm the menu appears.

---

## Task 3 — 06-workflows: Create Contoso-Job-Application-Triage workflow

**Demo folder:** `modules/02-agents/06-workflows/workflow-demo-py/`
**Script:** `invoke_workflow.py`
**Model:** `gpt-5.4`
**Credential:** `DefaultAzureCredential`

### Blocker

The script reads `WORKFLOW_NAME=Contoso-Job-Application-Triage` from `.env` and calls the Foundry workflows API. That workflow must exist and be published in the Foundry project.

### What to do

1. Check if the workflow already exists in Foundry using `mcp__azure-deploy__foundry` (try `workflow_list` or similar command with `projectEndpoint`).
2. If it exists, run `invoke_workflow.py` and confirm it streams output.
3. If it does not exist, create it in the Foundry portal (`ai.azure.com` → project → Build → Workflows → New) or programmatically. The workflow should process a job application — name it exactly `Contoso-Job-Application-Triage`.
4. Read `modules/02-agents/06-workflows/readme.md` for the workflow definition and inputs expected.

---

## Task 4 — 07-agent-framework: Sign in and verify

**Demo folder:** `modules/02-agents/07-agent-framework/helpdesk-agent-py/`
**Script:** `agent-framework.py`
**Model:** `gpt-4.1`
**Credential:** `AzureCliCredential` — requires `az login`

### What to do

1. Confirm `az login` is active: `az account show`
2. If not signed in, instruct the user: `! az login`
3. Run the script:
   ```powershell
   cd modules\02-agents\07-agent-framework\helpdesk-agent-py
   .venv\Scripts\Activate.ps1
   python agent-framework.py
   ```
4. At the prompt, press Enter to use the default: `Create a ticket for my issue`
5. Confirm the agent processes the helpdesk tickets and creates output.

---

## Task 5 — 08-multi-agent: Sign in and verify

**Demo folder:** `modules/02-agents/08-multi-agent\travel-team-py/`
**Script:** `agents.py`
**Model:** `gpt-4.1`
**Credential:** `AzureCliCredential` — requires `az login`

### What to do

1. Confirm `az login` is active: `az account show`
2. Run the script:
   ```powershell
   cd modules\02-agents\08-multi-agent\travel-team-py
   .venv\Scripts\Activate.ps1
   python agents.py
   ```
3. Script is non-interactive — it reads `data/travel_request.txt` and streams the SequentialBuilder output (destination_researcher → budget_planner → itinerary_writer).
4. Confirm all three agent outputs appear.

---

## Task 6 — 09-a2a: Sign in and verify

**Demo folder:** `modules/02-agents/09-a2a/podcast-a2a-py/`
**Script:** `run_all.py`
**Model:** `gpt-4.1`
**Credential:** `DefaultAzureCredential` (browser auth or `az login` in chain)

### What to do

1. Run the script:
   ```powershell
   cd modules\02-agents\09-a2a\podcast-a2a-py
   .venv\Scripts\Activate.ps1
   python run_all.py
   ```
2. Script starts 3 A2A servers on ports 10007 (title), 10008 (segment), 10009 (routing), then launches the client.
3. Press Enter at the prompt to use the default: `Plan a podcast episode about the rise of small language models. I need a catchy title and a segment breakdown.`
4. Confirm the routing agent delegates to title and segment agents and a structured response appears.
5. Press Ctrl+C to exit cleanly.

---

## Priority order

1. **04-foundry-iq** — needs session restart + MCP tools (most complex, do first)
2. **07, 08, 09** — just need `az login`, run in any order
3. **06-workflows** — depends on workflow existing in Foundry
4. **05-m365** — depends on M365 Copilot license (may be permanently blocked)
