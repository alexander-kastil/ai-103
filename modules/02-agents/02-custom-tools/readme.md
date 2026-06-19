# Integrate custom tools into your agent

https://learn.microsoft.com/en-us/training/modules/build-agent-with-custom-tools/

---

## Instructor Demo Guide

This demo shows how to extend a Foundry Agent Service agent by defining and wiring up custom Python functions as tools, using an astronomy assistant as a live example.

A complete, runnable solution lives next to this guide in [`astronomy-agent-py/`](astronomy-agent-py/) — you don't need to clone the lab repo to run it.

**Estimated time:** 25–35 minutes

---

### Prerequisites

- Python 3.13+ on the PATH
- An active Azure subscription with a Foundry project and a chat model deployed (e.g. `gpt-4.1`)
- Signed in to Azure: `az login` (the demo uses `DefaultAzureCredential`)
- Demo working directory: [`astronomy-agent-py/`](astronomy-agent-py/)
- **Azure AI Developer** role on the resource group — `Foundry User` is not sufficient. Assign it:

  ```bash
  az role assignment create \
    --assignee "<upn-or-object-id>" \
    --role "Azure AI Developer" \
    --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>"
  ```

This demo's Foundry project endpoint:

```
https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos
```

### One-time setup

From the [`astronomy-agent-py/`](astronomy-agent-py/) folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit .env if your deployment name differs
az login
```

`.env` already points `PROJECT_ENDPOINT` at the demo project above. Set `MODEL_DEPLOYMENT_NAME` to match your deployment.

---

### Step 1 — Explain the problem: why built-in tools fall short

Open the module landing page and show the learning objectives.

> **Talking point:** "The Agent Service ships with built-in tools for file search and code generation. But what if your agent needs to look up a customer order, query your inventory system, or in today's demo — find the next visible astronomical event? That requires a *custom tool*."

Show the diagram from unit 2 (agent calls a custom tool, tool calls an external service, result flows back to the user).

> **Talking point:** "The agent doesn't run your function directly. It decides it needs one, asks for it with arguments, your code runs the function, then you feed the result back. That's the loop."

---

### Step 2 — Explore the custom tool options

Open unit 3 in the browser and walk through the list briefly.

| Option | Best for |
|---|---|
| **Custom function (function calling)** | In-process logic, any language |
| **Azure Functions** | Serverless / event-driven workloads |
| **OpenAPI specification** | Any existing HTTP API with an OpenAPI 3.0 spec |
| **Azure Logic Apps** | Low-code / no-code workflow integration |

> **Talking point:** "Today we use function calling — the simplest option and the one the exercise covers. The pattern you learn transfers directly to Azure Functions and OpenAPI tools."

---

### Step 3 — Show the file layout

In VS Code, open [`astronomy-agent-py/`](astronomy-agent-py/) and point out:

- [`agent.py`](astronomy-agent-py/agent.py) — the main script: defines the tools, creates the agent, runs the chat loop
- [`functions.py`](astronomy-agent-py/functions.py) — the pre-built business logic (`next_visible_event`, `calculate_observation_cost`, `generate_observation_report`)
- [`data/`](astronomy-agent-py/data/) — flat-file "databases": `events.txt`, `telescope_rates.txt`, `priority_multipliers.txt`
- [`requirements.txt`](astronomy-agent-py/requirements.txt) — Azure AI Projects SDK, `azure-identity`, `openai`, `python-dotenv`

> **Talking point:** "The business logic is already written in `functions.py`. What matters in `agent.py` is the glue: the tool definitions that tell the agent *what* each function does and *what arguments it takes*."

---

### Step 4 — Define a function tool

In [`agent.py`](astronomy-agent-py/agent.py), show how `FunctionTool` wraps the existing function with a JSON schema description:

```python
from azure.ai.projects.models import FunctionTool

event_tool = FunctionTool(
    name="next_visible_event",
    description="Get the next visible astronomical event for a given location (continent).",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Continent to find the next visible event in, e.g. 'South America'."
            }
        },
        "required": ["location"],
        "additionalProperties": False
    },
    strict=True
)
```

> **Talking point:** "This is declarative — you are not calling the function here. You are describing it so the model can decide when and how to call it. The name and description are what the model reads. Make them meaningful."

Repeat briefly for `cost_tool` and `report_tool`, noting the additional parameters (`telescope_tier`, `hours`, `priority`).

---

### Step 5 — Create the agent with the toolset

Show the `create_version` call that registers all three tools with the agent:

```python
agent = project_client.agents.create_version(
    agent_name="astronomy-agent",
    definition=PromptAgentDefinition(
        model=model_deployment,
        instructions="""You are an astronomy observations assistant that helps
users find information about astronomical events and calculate
telescope rental costs. Use the available tools to assist.""",
        tools=[event_tool, cost_tool, report_tool]
    )
)
```

> **Talking point:** "Passing `tools=` into the agent definition is all it takes for the model to know these functions exist. The instructions reinforce when to use them."

---

### Step 6 — Handle the function-call loop

The agent is server-side; you drive it through the OpenAI-compatible **responses** API over a **conversation**. Point out the key pattern:

1. You send a prompt with `responses.create(...)` and an `agent_reference`
2. The agent returns output items — when `item.type == "function_call"`, the model is asking *you* to run code
3. Your code runs the matching Python function and posts the result back as a `FunctionCallOutput`
4. You send the outputs back with another `responses.create(...)`; the agent produces its final answer

```python
response = openai_client.responses.create(
    input=user_input,
    conversation=conversation.id,
    extra_body={"agent_reference": agent_reference},
)

function_outputs = []
for item in response.output:
    if item.type == "function_call":
        args = json.loads(item.arguments)
        if item.name == "next_visible_event":
            result = next_visible_event(**args)
        elif item.name == "calculate_observation_cost":
            result = calculate_observation_cost(**args)
        elif item.name == "generate_observation_report":
            result = generate_observation_report(**args)

        function_outputs.append(
            FunctionCallOutput(
                type="function_call_output",
                call_id=item.call_id,
                output=result,
            )
        )

response = openai_client.responses.create(
    input=function_outputs,
    conversation=conversation.id,
    extra_body={"agent_reference": agent_reference},
)
```

> **Talking point:** "Notice we are not calling any AI here. We are running plain Python. The model figured out the right function and arguments — we just execute it and hand back the result. In `agent.py` this is wrapped in a small `while` loop so chained calls — find the event, *then* price it — all resolve before we print the answer."

---

### Step 7 — Run the demo

From [`astronomy-agent-py/`](astronomy-agent-py/) with the virtual environment active:

```powershell
python agent.py
```

Send this prompt:

```
Find the next event visible from South America and calculate costs for 5 hours of premium telescope time at normal priority.
```

Expected output (the `[tool call]` lines come from the dispatcher in `agent.py`):

```
  [tool call] next_visible_event({'location': 'South America'})
  [tool call] calculate_observation_cost({'telescope_tier': 'premium', 'hours': 5, 'priority': 'normal'})

AGENT: The next astronomical event visible from South America is the Saturn-Mars
Conjunction on July 10th. The cost for 5 hours of premium telescope time at normal
priority is $1,875.
```

> **Note:** `next_visible_event` is date-aware — it returns the next event *after today*, so the named event changes as the year progresses (the cost is fixed at $1,875 regardless). Before May 1st it returns the Jupiter-Venus Conjunction; after that, the Saturn-Mars Conjunction; and so on through the list in [`data/events.txt`](astronomy-agent-py/data/events.txt).

> **Talking point:** "One user message, two tool calls. The agent chained them automatically. We never told it 'first call event lookup, then call cost calculator' — it decided that from context."

Optionally show the report tool by asking:

```
Generate an observation report for that session. My name is Ada Lovelace.
```

A `report_*.txt` file is written to the working directory.

Type `quit` to exit — the script deletes the agent version and the conversation on the way out.

---

### Step 8 — Cleanup

The demo cleans up its own agent version and conversation when you type `quit`. Remind students that after their own exercise they should also:

- Delete the model deployment in the Foundry portal / VS Code Foundry Toolkit
- Delete the Azure resource group to avoid ongoing charges

---

### Summary

| Topic covered | Where |
|---|---|
| Why custom tools matter over built-in tools | Unit 2 |
| Four custom tool options (function, Azure Functions, OpenAPI, Logic Apps) | Unit 3 |
| Writing a `FunctionTool` definition with JSON schema | `agent.py`, Step 4 |
| Creating an agent version with tools attached | `agent.py`, Step 5 |
| Handling `function_call` items and posting `FunctionCallOutput` back | `agent.py`, Step 6 |
| End-to-end test: astronomy assistant with two chained tool calls | Step 7 |
