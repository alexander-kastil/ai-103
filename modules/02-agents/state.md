# Agent Demo Run State

Last updated: 2026-06-17

## Environment

- PROJECT_ENDPOINT: https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos
- MODEL_DEPLOYMENT_NAME (default): gpt-5.4
- Azure subscription: cd091145-5ea2-4703-ba5d-41063b1d4308
- Tenant: d92b247e-90e0-4469-a129-6a32866c0d0a

## Demo Status

| Demo | Folder | Script | Model | Status | Remaining blocker |
|---|---|---|---|---|---|
| 04-foundry-iq | fabrikam-audio-py | agent_client.py | gpt-4.1 | Azure resources created | Knowledge base + agent not yet created (needs session restart + microsoft-foundry MCP) |
| 05-m365 | store-ops-workiq-py | workiq_demo.py | gpt-5.4 | Ready | Work IQ installed + EULA accepted; M365 license verified via Graph proxy (direct WorkIQ endpoint not provisioned, optional `workiq auth consent`) |
| 06-workflows | workflow-demo-py | invoke_workflow.py | gpt-5.4 | Ready | Workflow published (active, v2) + Screening-Agent/Response-Agent created on gpt-5.4; YAML at 06-workflows/Contoso-Job-Application-Triage.yaml |
| 07-agent-framework | helpdesk-agent-py | agent-framework.py | gpt-4.1 | Ready | az login |
| 08-multi-agent | travel-team-py | agents.py | gpt-4.1 | Ready | az login |
| 09-a2a | podcast-a2a-py | run_all.py | gpt-4.1 | Ready | az login |

## 04-foundry-iq — Azure resources

| Resource | Name | Endpoint |
|---|---|---|
| AI Search (free) | ai103demossearch | https://ai103demossearch.search.windows.net |
| Storage account | ai103demosstorage | https://ai103demosstorage.blob.core.windows.net/ |
| Blob container | fabrikam-audio | 3 Markdown product files uploaded |

- Admin key in `.claude/deploy.config` (`AZURE_AI_SEARCH_API_KEY`)
- RBAC: Search Index Data Contributor + Search Service Contributor → Foundry managed identity `aa359067-b96a-48fe-9699-75f7615b082f`
- `.mcp.json` fixed: `mcp>=1.0,<2.0` pinned, `--envFile .claude/deploy.config`

**Next:** Restart Claude Code → use `mcp__microsoft-foundry__*` to create `kb-fabrikam-audio` and `fabrikam-audio-agent`, then set approval mode in VS Code Foundry Toolkit.

## Run Commands

```powershell
# 04
cd modules\02-agents\04-foundry-iq\fabrikam-audio-py
.venv\Scripts\Activate.ps1; python agent_client.py

# 05
cd modules\02-agents\05-m365\store-ops-workiq-py
.venv\Scripts\Activate.ps1; python workiq_demo.py

# 06
cd modules\02-agents\06-workflows\workflow-demo-py
.venv\Scripts\Activate.ps1; python invoke_workflow.py

# 07
cd modules\02-agents\07-agent-framework\helpdesk-agent-py
.venv\Scripts\Activate.ps1; python agent-framework.py

# 08
cd modules\02-agents\08-multi-agent\travel-team-py
.venv\Scripts\Activate.ps1; python agents.py

# 09
cd modules\02-agents\09-a2a\podcast-a2a-py
.venv\Scripts\Activate.ps1; python run_all.py
```
