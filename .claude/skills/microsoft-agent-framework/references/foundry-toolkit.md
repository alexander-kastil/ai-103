# Foundry Toolkit for VS Code

The **Microsoft Foundry Toolkit** (repo: `github.com/microsoft/foundry-toolkit`) is a **VS Code extension**, not a CLI. It is the rebranded "AI Toolkit for VS Code" — **GA (April 2026)**, MIT-licensed. It unifies model discovery, prompt experimentation, agent scaffolding, local debugging, evaluation, tracing, and deployment to Microsoft Foundry in one IDE surface.

> The "CLI" parts of the workflow come from companion tools (`az`, `azd`, the Agent Framework SDK), not from the toolkit itself. The toolkit **composes** with them — it does not replace them.

## How it composes

```
Agent Framework SDK   →  write the agent logic (tools, instructions, responses)
Foundry Toolkit (VS)  →  scaffold, run/debug locally, evaluate, trace, trigger deploy
azd                   →  provision infra + deploy (azd provision / azd deploy)
Foundry Agent Service →  managed runtime
```

Workspace files that tie them together: `azure.yaml` (azd services), `.azure/<env>/.env` (azd env), `agent.yaml` (agent config), `eval.yaml` (eval intent), `.foundry/agent-metadata.yaml` (non-secret overlay state).

## Install

- Install from the VS Code marketplace: `aka.ms/foundrytk`. Reload VS Code, then sign in with the Azure account that has Foundry project access.
- **Local prototyping** (GitHub-hosted models + Playground) needs no Azure subscription.
- **Production features** need: Azure CLI (`az login`), `azd` (`azd auth login`), Node.js 18+ (for MCP via `npx`), Git, a Foundry project, and roles **Foundry Owner/User** on the project + Contributor on the subscription.

## Capabilities

**Models**: Model Catalog (Foundry, Foundry Local, GitHub, OpenAI, Anthropic, Google, NVIDIA NIM, ONNX, Ollama), Playground, fine-tuning (local GPU or Azure Container Apps), conversion/optimization, performance profiling via Windows ML.

**Agents**:
- **Agent Builder** — no-code prompt-agent design.
- **Create a New Hosted Agent** command — scaffolds a code-based hosted-agent project (`agent.yaml` + `main.py` + `Dockerfile` + `requirements.txt`).
- **Tool Catalog / Toolbox** — MCP server integration + unified tool config (with Guardrails).
- **Agent Inspector** — local debug with streaming/trace visualization, launched via **F5**; agents respond on `localhost:8088`.
- **Hosted Agent Playground** — chat + tracing.
- **Evaluation framework** — built-in metrics, batch + continuous eval (GA).
- **Tracing/monitoring** — OpenTelemetry-based.

**Foundry integration**: browse/manage Foundry resources, deploy models, and create/deploy/test hosted agents through the Foundry Agent Service.

## Hosted-agent flow in the IDE

1. **Scaffold** — "Create a New Hosted Agent" generates the project.
2. **Test locally** — F5 → Agent Inspector; agent on `localhost:8088`.
3. **Deploy** — build image → push to ACR → Foundry pulls and runs it; or use **ZIP code deploy** / **bring-your-own-image (BYOI)**. Underneath this is the `azd` flow (see [`agent-framework-deploy`](agent-framework-deploy.md) → Hosted Agent Deployment).
4. **Validate** — Foundry Playground or VS Code Playground.

## Bundled skills

The toolkit ships coding-agent skills `vscode-microsoft-foundry` and `foundrytk-quick-start`, plus access to the core `microsoft-foundry` skill.

## Samples & labs

- `samples/hosted-agent` in the repo (incl. LangGraph hosted-agent samples).
- Hands-on lab repo `github.com/microsoft-foundry/Foundry_Toolkit_for_VSCode_Lab` — single-agent and multi-agent labs using Agent Framework (Python).
- `Azure-Samples/Foundry_Toolkit_Samples`.

## When to recommend it

- A developer wants an **IDE-first** loop: scaffold → F5 debug → eval → deploy without leaving VS Code.
- You need the **Model Catalog / Playground** to compare or deploy models.
- You want built-in **eval + tracing** wired up with minimal config.

For headless / scripted / CI provisioning, prefer the SDK or `azd` paths in [`agent-framework-deploy`](agent-framework-deploy.md) instead.
