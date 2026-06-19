---
name: microsoft-agent-framework
description: >-
  Master skill for Microsoft Foundry + Microsoft Agent Framework (Python) development — agent patterns,
  deployment path selection (prompt agent via azure-ai-projects SDK, hosted agent via azd/container/ZIP),
  the Foundry Toolkit for VS Code, publishing to M365/Teams via the Agent 365 CLI, evaluation, tools, and
  .NET↔Python API bridging. Delegates to task-oriented leaf skills. Use when working on any Foundry or
  Agent Framework project in this repo.
  Triggers on: "agent framework", "maf", "foundry", "magentic", "workflow builder", "hosted agent",
  "prompt agent", "foundry agent", "agent deployment", "deploy to foundry", "file search", "azd ai agent",
  "foundry toolkit", "agent 365", "publish to teams", "agent eval",
  "work iq", "workiq", "m365 data", "work iq setup",
  "work iq error", "workiq troubleshooting", "workiq 403", "wam error", "workiq ebusy",
  "run demo error", "unicodeencodeerror", "charmap codec", "cp1252", "emoji crash",
  "servers won't shut down", "ctrl_break", "process group", "health check timeout",
  "address already in use", "function tool not supported", "a2a run error",
  "declarative workflow", "csdl", "power fx", "powerfx", "conditiongroup", "foreach", "set variable",
  "if else workflow", "workflow empty canvas", "workflow routing not running", "invokeazureagent",
  "sendactivity", "workflowagentdefinition", "portal workflow", "visual designer", "agent_reference".
license: Complete terms in LICENSE.txt
---

# microsoft-agent-framework — Agent Framework Router

Routes Agent Framework requests to the appropriate leaf skill. Do not implement directly — delegate immediately.

## Delegate Map

| Request type | Leaf skill to invoke |
| --- | --- |
| Add/edit agents, change workflow topology, orchestration (code-first `WorkflowBuilder` SDK) | [`agent-framework-workflow`](references/agent-framework-workflow.md) |
| Build/publish a **Foundry portal** workflow (CSDL YAML); empty-canvas or routing-never-runs bugs; `ConditionGroup` / `Foreach` dialect | [`foundry-workflow-declarative`](references/foundry-workflow-declarative.md) |
| Write/debug **Power Fx** expressions in a portal workflow (conditions, values, `.`-on-Text errors, scopes) | [`foundry-workflow-powerfx`](references/foundry-workflow-powerfx.md) |
| Design workflow architectures, choose patterns, reference topologies | [`agent-framework-orchestration`](references/agent-framework-orchestration.md) |
| Coordinate .NET ↔ Python contracts, API endpoints, DTOs | [`agent-framework-api-bridge`](references/agent-framework-api-bridge.md) |
| Deploy a prompt agent (SDK) OR a hosted agent (azd / container / ZIP) | [`agent-framework-deploy`](references/agent-framework-deploy.md) |
| Build / debug / eval an agent from the VS Code Foundry Toolkit | [`foundry-toolkit`](references/foundry-toolkit.md) |
| Publish an agent to Microsoft 365 / Teams; govern its Entra identity | [`agent-365-cli`](references/agent-365-cli.md) |
| Eval datasets, batch eval, prompt optimization | [`agent-framework-eval`](references/agent-framework-eval.md) |
| Connect an agent to live M365 data with Work IQ; provision / consent / bill Work IQ | [`work-iq-setup`](references/work-iq-setup.md) |
| Diagnose a failing Work IQ install / auth / consent / billing / query | [`work-iq-troubleshooting`](references/work-iq-troubleshooting.md) |
| Diagnose a demo that fails when **run locally** (encoding crash, servers won't start / shut down, port in use, model tool support) | [`agent-framework-run-troubleshooting`](references/agent-framework-run-troubleshooting.md) |

> **Work IQ vs Agent 365 CLI**: Work IQ reads live M365 data *into* an agent (mail, calendar, Teams); the Agent 365 CLI publishes an agent *out* to Teams/M365 as a registered identity. They are complementary, not alternatives.

> **Deployment path by agent type** (do not default to raw `az rest`):
> - **Prompt agent** (instructions + model + tools) → `azure-ai-projects` 2.x SDK: `project.agents.create_version(PromptAgentDefinition(...))`. See `agent-framework-deploy.md`.
> - **Hosted agent** (your own code) → `azd ai agent` (`microsoft.foundry` extension) or the SDK ZIP path. See `agent-framework-deploy.md`.
> - **Publish to Teams/M365** → Agent 365 CLI (`a365`). See `agent-365-cli.md`.

## Shared References

- [Stack Versions](references/stack-versions.md) — Current package versions, model client decision table, orchestration decision table
- [Code Patterns](references/agent-framework-patterns.md) — FoundryChatClient, MagenticBuilder, WorkflowBuilder, non-Foundry models
