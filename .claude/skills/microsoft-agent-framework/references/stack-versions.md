# Stack Versions & Model Clients

## Current Stack Versions (as of April 2026)

### Foundry SDK (prompt agents, files, vector stores, models)

- **azure-ai-projects**: `>=2.0.0` (latest `2.2.0`) — the Microsoft Foundry SDK. Exposes `.agents.create_version(PromptAgentDefinition(...))`, `.get_openai_client()`, `.connections`, `.deployments`, `.indexes`. `FileSearchTool` / `PromptAgentDefinition` live under `azure.ai.projects.models`.
  - **2.x is incompatible with 1.x.** The 1.x `client.agents.create_agent(...)` is replaced by 2.x `client.agents.create_version(...)`.
  - Hosted-agent ZIP deploy needs `>=2.2.0` + `allow_preview=True`; container deploy needs `>=2.1.0`.
- **azure-identity** — `DefaultAzureCredential` (local) / `ManagedIdentityCredential` (Azure).

### Agent Framework (orchestration, hosting bridge)

- **agent-framework**: `1.2.2`
- **agent-framework-openai**: `1.2.2` (for non-Foundry models via `OpenAIChatCompletionClient`)
- **agent-framework-foundry**: `1.2.2` (for Foundry models via `FoundryChatClient`)
- **agent-framework-foundry-hosting**: `1.0.0a260429` (alpha — `ResponsesHostServer` bridge for hosted agents)
- **agent-framework-orchestrations**: `1.0.0b260429` (beta — `MagenticBuilder`, `WorkflowBuilder`)
- **openai**: `2.33.0` (pulled by `agent-framework-openai`)

## Deployment Path Decision

| Agent type | Path | Surface |
|---|---|---|
| Prompt agent (instructions + model + tools) | `azure-ai-projects` 2.x SDK | `project.agents.create_version(PromptAgentDefinition(...))` |
| Hosted agent (custom code) | `azd ai agent` (`microsoft.foundry` ext) or SDK ZIP/container | `azd deploy` / `project.beta.agents.create_version_from_code` |
| Publish to Teams / M365 | Agent 365 CLI | `a365 setup all` → `a365 publish` |
| IDE-first build/debug/eval | Foundry Toolkit for VS Code | F5 → Agent Inspector → deploy |

## Foundry RBAC Roles (renamed)

| Current | Former | Grants |
|---|---|---|
| **Foundry User** | Azure AI User | Data-plane use; runtime agent identity needs this for models/tools |
| **Foundry Project Manager** | Azure AI Project Manager | Deploy agents + assign Foundry User to the agent identity |
| **Foundry Owner** | Azure AI Owner | Full control of the Foundry resource |
| **Foundry Account Owner** | Azure AI Account Owner | Account-level control |

## Model Client Decision

| Scenario | Client | Package |
|---|---|---|
| Microsoft Foundry deployment | `FoundryChatClient(model=..., credential=...)` | `agent-framework-foundry` |
| OpenAI / Azure OpenAI | `OpenAIChatClient(model=...)` (Responses API) | `agent-framework-openai` |
| DeepSeek, Ollama, LM Studio, vLLM | `OpenAIChatCompletionClient(model=..., base_url=..., api_key=...)` (Chat Completions API) | `agent-framework-openai` |

**Key finding**: Third-party providers (DeepSeek, etc.) only support the Chat Completions API. `OpenAIChatClient` uses the Responses API and will 404. Always use `OpenAIChatCompletionClient` with `base_url` for non-Foundry/non-Azure-OpenAI models.

## Orchestration Decision

| Scenario | Pattern |
|---|---|
| Fixed pipeline (known steps, pre-defined edges) | `WorkflowBuilder` — `add_edge()`, `add_switch_case_edge_group()` |
| Dynamic coordination (manager decides next agent) | `MagenticBuilder` — manager plans, delegates, tracks via ledger |

## Package Upgrade Constraints

### azure-ai-agentserver-agentframework (legacy bridge)

`azure-ai-agentserver-agentframework==1.0.0b17` pins:
- `agent-framework-core<=1.0.0rc3`
- `agent-framework-azure-ai<=1.0.0rc3`

The GA packages (`1.0.x`) renamed `BaseContextProvider` → `ContextProvider`, which breaks the agentserver bridge import. **Never upgrade `agent-framework-core` or related packages past `rc3` without also upgrading agentserver.**

Before any package change in a venv using this bridge:

```bash
pip show azure-ai-agentserver-agentframework
pip install <package>==<version> --dry-run
```

> Note: The current stack (April 2026) has migrated to `agent-framework-foundry-hosting` (`ResponsesHostServer`), which replaces the agentserver bridge entirely. This constraint only applies to projects still on the `b17` bridge.
