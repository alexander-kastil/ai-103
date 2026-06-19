# Develop an AI agent with Microsoft Agent Framework

https://learn.microsoft.com/en-us/training/modules/develop-ai-agent-with-semantic-kernel/

---

## Instructor Demo Guide

This demo shows how to build a Microsoft Foundry Agent using the Microsoft Agent Framework SDK — connecting to a Foundry project, creating an agent with a system prompt, extending it with a custom `@tool` function, and running it against real input — using an **IT helpdesk ticket-submission** scenario. The agent reads a raw user complaint and automatically calls a `create_ticket` tool to file a support ticket. This deliberately uses a different domain than the student lab (which builds an expense-claim email agent) so the mechanics stand out, not the scenario.

The complete runnable solution for this demo lives in [`helpdesk-agent-py/`](helpdesk-agent-py/) — no need to clone the lab repo.

**Estimated time:** 20–25 minutes

---

## Prerequisites

- Azure subscription with a Microsoft Foundry project deployed
- gpt-4.1 (or equivalent) model deployed in that project; project endpoint URL ready
- Azure CLI installed and signed in (`az login` completed)
- Python 3.13+ with a virtual environment
- `agent_framework` package installed (`pip install -r requirements.txt`)
- VS Code with the Foundry Toolkit extension (optional but recommended for project setup)

---

## One-time setup

Run these once before the demo, from the [`helpdesk-agent-py/`](helpdesk-agent-py/) folder:

```powershell
cd modules/02-agents/07-agent-framework/helpdesk-agent-py
python -m venv labenv
.\labenv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME
az login
```

> **Talking point:** "The SDK authenticates via `AzureCliCredential` — no API keys in code. Because I've already run `az login`, the agent picks up my Azure identity automatically. For production you'd use a managed identity or service principal, but the calling pattern is identical."

---

## Step 1 — Orient the audience: what is Microsoft Agent Framework?

> **Talking point:** "The Microsoft Agent Framework is an open-source SDK that sits on top of the Microsoft Foundry Agent Service. It gives you a consistent agent interface regardless of provider — Foundry, Azure OpenAI, Anthropic, Copilot Studio — so you can swap providers without rewriting your code. Today we focus on Foundry Agents, which are the enterprise tier: managed threads, built-in tool support, RBAC, no infrastructure to manage."

Draw attention to the core components on the whiteboard or slide:

| Component | What it does |
|---|---|
| `Agent` | Main class combining client, instructions, and tools |
| `AzureOpenAIResponsesClient` | Connects to the Foundry project endpoint |
| `AgentSession` | Persists conversation history across turns |
| `@tool` decorator | Registers a Python function the model can call |
| Built-in tools | Code Interpreter, File Search, Web Search — zero config |
| Workflow orchestration | Sequential, parallel, group-chat, handoff patterns |

---

## Step 2 — Show the project and environment setup

1. Open the [`helpdesk-agent-py/`](helpdesk-agent-py/) folder in VS Code.

2. Show the four self-contained files: `agent-framework.py`, `tickets.txt`, `requirements.txt`, and `.env.example`.

3. Open `.env` and confirm the two values copied from the Foundry project:

    ```
    PROJECT_ENDPOINT=<your_project_endpoint>
    MODEL_DEPLOYMENT_NAME=gpt-4.1
    ```

4. Open `tickets.txt` and read one of the raw issues out loud — for example the Wi-Fi outage. Point out that this is unstructured natural language, exactly what a real helpdesk inbox looks like.

> **Talking point:** "Notice there's no structure here — no category, no priority field. The agent has to read the complaint, reason about it, and fill in the structured ticket fields itself. That's the difference between a script and an agent."

---

## Step 3 — Walk through the imports

Open `agent-framework.py` and point to the imports:

```python
from agent_framework import tool, Agent
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from pydantic import Field
from typing import Annotated
```

> **Talking point:** "Notice `pydantic.Field` and `typing.Annotated`. These are how we embed descriptions directly on function parameters so the model knows what each argument means and when to call the function — this is the function-calling contract. `load_dotenv` pulls our endpoint and deployment name out of the `.env` file."

---

## Step 4 — Define a custom tool with `@tool`

Show the `create_ticket` function:

```python
@tool(approval_mode="never_require")
def create_ticket(
    category: Annotated[str, Field(description="The category of the issue, e.g. Hardware, Software, Network, Account, or Security.")],
    priority: Annotated[str, Field(description="The priority of the ticket: Low, Medium, High, or Critical.")],
    summary: Annotated[str, Field(description="A concise summary of the reported issue.")]):
        print("\nCategory:", category)
        print("Priority:", priority)
        print("Summary:", summary, "\n")
```

> **Talking point:** "The `@tool` decorator does two things: it generates a JSON schema from the type hints and `Field` descriptions, and it registers the function with the framework. `approval_mode='never_require'` means the agent calls it automatically — no human-in-the-loop confirmation needed. You'd flip that to `'always_require'` for anything that has real side effects, like actually opening a ticket in ServiceNow."

Point out the three parameters: `category`, `priority`, `summary` — and note that the descriptions guide the model to populate them correctly from the complaint text. In a real app this function would call your ticketing system's API; here it prints to the console to keep the demo focused.

---

## Step 5 — Create the agent and connect to Foundry

Show the agent initialization block inside `process_helpdesk_issues`:

```python
credential = AzureCliCredential()

async with (
    Agent(
        client=AzureOpenAIResponsesClient(
            credential=credential,
            deployment_name=os.getenv("MODEL_DEPLOYMENT_NAME"),
            project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        ),
        instructions="""You are an AI assistant for an IT helpdesk.
                    At the user's request, read the reported IT issue and use the plug-in function
                    to create a support ticket. Choose an appropriate category
                    (for example: Hardware, Software, Network, Account, or Security),
                    set a priority of Low, Medium, High, or Critical based on the impact described,
                    and write a concise summary of the problem.
                    Then confirm to the user that you've created the ticket.
                    Don't ask for any more information from the user, just use the data provided
                    to create the ticket.""",
        tools=[create_ticket],
    ) as agent,
):
```

> **Talking point:** "Three things to highlight here. First, `AzureOpenAIResponsesClient` is the Foundry adapter — swap it for `OpenAIResponsesClient` to point at OpenAI instead, same code. Second, `instructions` is the system prompt — this is where we tell the agent to pick a category and a priority. Notice we let the *model* decide the priority based on the impact described in the complaint. Third, `tools=[create_ticket]` registers our function; you can pass a list of as many functions as you need and the model picks the right one."

---

## Step 6 — Run the agent and observe automatic tool invocation

Show the execution block:

```python
try:
    prompt_messages = [f"{prompt}: {issues_data}"]
    response = await agent.run(prompt_messages)
    print(f"\n# Agent:\n{response}")
except Exception as e:
    print(e)
```

Run it live:

```powershell
az login   # if not already signed in
python agent-framework.py
```

When prompted, type: `Create a ticket for my issue`

> **Talking point:** "Watch the output — you'll see the `Category:`, `Priority:`, and `Summary:` printed by our `create_ticket` function, then the agent's natural language confirmation. The model read the raw complaint, decided on its own to call `create_ticket`, classified the issue, set a priority, and the framework routed the call and returned the result back to the model for the final reply. We wrote zero orchestration logic."

Point out what the output looks like (for the security-incident issue, the model should pick a high or critical priority):

```
Category: Security
Priority: Critical
Summary: Possible account compromise — unsolicited password reset emails and unrecognized sent messages.

# Agent:
I've created a Critical-priority Security ticket for the suspected account compromise ...
```

---

## Step 7 — Explain what happens behind the scenes

> **Talking point:** "Internally the framework creates an `AgentSession` which holds the thread — conversation history is stored server-side in Foundry, not in your app. If the user sends a follow-up message you pass it to the same session and the model has full context. The session is what distinguishes a stateless API call from a real agent conversation."

Summarise the flow on the whiteboard:

```
Raw complaint
   → Agent.run()
      → Model sees system prompt + complaint + tool schema
         → Model emits tool_call: create_ticket(category=..., priority=..., summary=...)
            → Framework invokes create_ticket()
               → Result returned to model
                  → Model generates final confirmation
                     → Response printed
```

---

## Step 8 — Mention built-in tools and next steps

> **Talking point:** "Everything we just did used a custom function tool. Foundry also ships three built-in tools you can enable with a single parameter: `CodeInterpreterTool()` for Python execution, `FileSearchTool()` for RAG over documents — imagine grounding the agent in your IT knowledge base — and `WebSearchTool()` for live internet access. You add them to the `tools=[]` list alongside your custom functions — the model decides which to call. Multi-agent orchestration — having a triage agent hand off to a specialist agent — is the topic of the next module."

---

## Cleanup reminder

- Delete the deployed model via the Foundry Toolkit extension.
- Delete the Azure resource group to avoid ongoing charges.

---

## Summary

| What was demonstrated | Key concept |
|---|---|
| `AzureOpenAIResponsesClient` connecting to a Foundry project | SDK abstracts provider connection |
| `Agent` with `instructions` and `tools` | System prompt + tool registration in one object |
| `@tool` decorator with `Annotated` / `Field` | Auto-generates JSON schema for function calling |
| `approval_mode="never_require"` | Controls human-in-the-loop for tool invocation |
| Model classifies category and priority from raw text | The agent reasons over unstructured input |
| `agent.run(messages)` executing automatically | Framework handles tool routing — no manual parsing |
| `AgentSession` thread management | Server-side conversation state in Foundry |
| Built-in tools (Code Interpreter, File Search, Web Search) | Zero-config capabilities ready to add |

Students will now complete the exercise themselves, building an **expense-claim email agent** with a `submit_claim` tool — same SDK mechanics, different domain:
[Exercise — Develop an Azure AI agent with the Microsoft Agent Framework SDK](https://learn.microsoft.com/en-us/training/modules/develop-ai-agent-with-semantic-kernel/5-exercise)
