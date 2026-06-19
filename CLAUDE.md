# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

**AI-103: Develop AI apps and agents on Azure** — a training delivery repository with instructor demos (modules) and hands-on labs for building AI solutions using Azure AI Foundry and the Microsoft Agent Framework SDK.

## Running Code

Each demo and lab is a self-contained Python project in its own `*-py/` directory. The pattern is consistent:

```bash
cd modules/01-gen-ai/03-chat-app/chat-demo-py
pip install -r requirements.txt
cp .env.example .env   # then fill in your Azure credentials
python chat-demo.py
```

Environment variables always come from `.env` (never committed). The critical variables are:
- `PROJECT_ENDPOINT` — Azure AI Foundry project endpoint
- `MODEL_DEPLOYMENT_NAME` — deployed model name in the Foundry project

Additional variables per module are documented in each `.env.example`.

## Repository Structure

```
modules/     # Instructor demos, organized by learning unit
  01-gen-ai/        # Generative AI apps (chat, tools, responsible AI)
  02-agents/        # AI agents (custom tools, MCP, multi-agent, A2A)
  03-language/      # NLP: text analysis, speech, translation
  04-insights/      # Vision, image/video gen, document intelligence
labs/        # Student hands-on exercises (mirrors module structure)
tooling/     # Setup guides: Git, VS Code, Azure CLI, REST client
demos/       # Additional instructor materials
```

Each module subdirectory contains a numbered `*-py/` folder (the runnable demo) alongside a `readme.md` explaining the topic.

## Code Patterns

**Standard imports and client setup:**
```python
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
project_client = AIProjectClient(
    endpoint=os.getenv("PROJECT_ENDPOINT"),
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    ),
)
```

**Agent tool definitions** use `FunctionTool` from `azure.ai.projects.models`. Function parameters are described as JSON Schema dicts passed directly to the model.

**Creating/deploying Foundry agents** use the Microsoft Foundry SDK `azure-ai-projects` **2.x**: `project.agents.create_version(PromptAgentDefinition(...))` for prompt agents (with `FileSearchTool` for grounding). The 1.x `create_agent(...)` shape is superseded. Pick the deployment path by agent type — prompt agent → SDK, hosted agent → `azd`, publish to Teams/M365 → Agent 365 CLI. The `foundry-expert` agent and the `microsoft-agent-framework` skill own this.

**Console clearing** at script start: `os.system('cls' if os.name == 'nt' else 'clear')`.

## Dev Container

`.devcontainer/` provides a fully configured VS Code Remote Container with Node.js 20 and .NET 9 pre-installed. Open the repo in VS Code and choose "Reopen in Container" to use it.

## MCP Servers

`.mcp.json` configures Playwright, Azure Deploy, GitHub, Microsoft Learn, and Chrome DevTools MCP servers for use with agents and Claude Code tooling in this repo.

## Claude Code Skills & Agents

`.claude/skills/mermaid-diagram` — invoke with `/mermaid-diagram` to generate Mermaid diagrams (flowcharts, sequences, ERDs, architecture diagrams).

`.claude/skills/microsoft-agent-framework` — router skill for Microsoft Foundry + Agent Framework (Python) work. Delegates to task-oriented leaf references: `agent-framework-deploy` (prompt agent via SDK, hosted agent via azd/container/ZIP), `foundry-toolkit` (VS Code Foundry Toolkit), `agent-365-cli` (publish to M365/Teams), `agent-framework-workflow` / `-orchestration` / `-eval`, `stack-versions`, `agent-framework-patterns`. Used by the `foundry-expert` agent.

`.claude/agents/foundry-expert.md` — subagent (`foundry-expert`) for the full Foundry + Agent Framework lifecycle: scaffolding, coding, choosing the deployment path, deploying to Foundry (SDK / azd / Foundry Toolkit), evaluation, and publishing via the Agent 365 CLI.

**Expert agents must be used when present.** If a task falls within an expert agent's scope, delegate to it — do not handle it inline.

## Hard Rules

- YOU MUST NOT commit or push without explicit user request.
- Internal links use relative paths; anchors use `#heading-name`.
- Code fences must declare a language (`bash`, `python`, `json`, …).
- If a quality check fails, fix the underlying issue — do not bypass with `--no-verify`.
- Write clean code with no noise: no inline comments, no explanatory remarks, no placeholder notes.
- No error handling in scripts unless explicitly requested.
- No experimental or test files in the root directory — use `.claude/experiments/`, `e2e/images/`, `docs/`, or `labs/`.
- **Shell tool preference** — Always use Bash for shell operations. Use PowerShell only when a task is Windows-specific and Bash cannot handle it.
- **Running apps** — Before starting any dev server or background process, check if one is already running on that port. Re-use the existing instance. Never start a new server without explicit user permission or request.
- **Browser inspection** — Always prefer `chrome-devtools` MCP for UI verification, layout checks, and debugging. Only use Playwright when running automated test suites (`e2e/`).

## Workflow Orchestration

**Plan Node Default** — Enter plan mode for any non-trivial task (3+ steps or architectural decisions). Stop and re-plan if something goes sideways.

**Subagent Strategy** — Use subagents to keep the main context clean. Offload research, exploration, and parallel analysis. One task per subagent. Spawn parallel subagents wherever tasks are independent — do not serialize work that can run concurrently. For longer or multi-phase tasks, use dynamic workflows to fan out, verify, and synthesize across agents.

**Self-Improvement Loop** — After any user correction, update `tasks/lessons.md` with the pattern. Review lessons at session start.

**Verification Before Done** — Never mark a task complete without proving it works. Run tests, check logs, demonstrate correctness.

**Demand Elegance** — For non-trivial changes, pause and ask "is there a more elegant way?" Skip for simple, obvious fixes.

**Autonomous Bug Fixing** — When given a bug report, just fix it. Point at logs, errors, failing tests — then resolve them.

## Task Management

1. **Plan First** — write plan to `tasks/todo.md` with checkable items
2. **Verify Plan** — check in before starting implementation
3. **Track Progress** — mark items complete as you go
4. **Capture Lessons** — update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First** — make every change as simple as possible, impact minimal code
- **No Laziness** — find root causes, no temporary fixes, senior developer standards
- **Minimal Impact** — changes touch only what's necessary
- **Small fixes → minimal diff** — do not rewrite a section to fix a typo

## Token Efficiency

- Never re-read files you just wrote or edited.
- Never re-run commands to verify unless the outcome was uncertain.
- Do not echo back large blocks of code or file contents unless asked.
- Batch related edits into single operations.
- Do not summarize what you just did unless the result is ambiguous.

## Key Conventions

- All runnable code is Python 3.x; no TypeScript/JavaScript in demos
- Directories use numeric prefixes for ordering (`01-`, `02-`, etc.)
- Each `*-py/` directory is fully self-contained with its own `requirements.txt` and `.env.example`
- Lab exercises in `labs/` correspond 1-to-1 with module topics and link to Microsoft Learn learning paths
- Never commit `.env` files; the `.gitignore` excludes them
