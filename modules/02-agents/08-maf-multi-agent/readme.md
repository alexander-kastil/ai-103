# Develop a multi-agent solution with the Microsoft Agent Framework

https://learn.microsoft.com/en-us/training/modules/orchestrate-semantic-kernel-multi-agent-solution/

---

## Instructor Demo Guide

This demo shows how to build a multi-agent pipeline using the Microsoft Agent Framework SDK — running a **sequential** workflow that turns a single travel request into a finished trip plan through three specialized agents: a **Destination-Researcher**, a **Budget-Planner**, and an **Itinerary-Writer**. Each agent's output becomes the next agent's input, so the team collaborates to produce something no single agent was prompted to do alone.

The orchestration pattern is the same one the students use in their own lab (customer-feedback triage); only the domain is different, so you can present the *concept* with a fresh scenario and leave the lab as their hands-on practice.

A complete, runnable solution lives next to this guide in [`travel-team-py/`](travel-team-py/) — you don't need to clone the lab repo to run it.

**Estimated time:** 25–35 minutes

---

### Prerequisites

- Python 3.13+ on the PATH (the lab was tested with 3.13.x)
- An active Azure subscription with a Foundry project and a `gpt-4.1` chat model deployed (Global Standard)
- Signed in to Azure: `az login` (the demo authenticates via `AzureCliCredential`)
- Demo working directory: [`travel-team-py/`](travel-team-py/)

This demo's Foundry project endpoint:

```
https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos
```

### One-time setup

From the [`travel-team-py/`](travel-team-py/) folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit .env if your deployment name differs
az login
```

`.env` already points `PROJECT_ENDPOINT` at the demo project above. Set `MODEL_DEPLOYMENT_NAME` to match your deployment.

---

### Step 1 — Introduce the Microsoft Agent Framework

Open the MS Learn module page and the unit **"Understand the Microsoft Agent Framework."**

Explain the three building blocks:

- **Agents** — AI-driven entities that combine an LLM, instructions, optional tools, and conversation history to complete tasks autonomously.
- **Chat clients** — Provider-agnostic abstractions (`AzureAIAgentClient`, `AzureOpenAIChatClient`, etc.) behind a shared interface. You can swap providers without rewriting agent logic.
- **Agent orchestration** — Multiple agents collaborating via structured workflows; the SDK handles coordination so you focus on agent design.

> **Talking point:** "A single agent is powerful, but it's constrained by one set of instructions and one prompt. Multi-agent orchestration lets you assign distinct skills to each agent and combine their outputs — turning a monolith into a specialist team. Today that team plans a trip: one agent picks the destination, one budgets it, one writes the day-by-day itinerary."

---

### Step 2 — Explain Workflows: Executors, Edges, and Events

Open the unit **"Understand agent orchestration"** and walk through the workflow anatomy:

| Component | Role |
|---|---|
| **Executor** | A worker unit — either an AI agent or custom logic. Receives input, produces output. |
| **Edge** | Defines how messages flow: Direct, Conditional, Switch-Case, Fan-Out, or Fan-In. |
| **Event** | Observable signals (`WorkflowStartedEvent`, `ExecutorInvokeEvent`, `WorkflowOutputEvent`, etc.) for monitoring and debugging. |

> **Talking point:** "Edges are where the orchestration logic lives. A fan-out edge sends the same message to several agents at once; a switch-case edge routes one agent's output to a different downstream executor based on its result. Our travel team uses the simplest case — direct edges chained one after another."

---

### Step 3 — Tour the Five Orchestration Patterns

Show a quick visual comparison using the diagrams from the module units:

| Pattern | Description | Best for |
|---|---|---|
| **Concurrent** | All agents receive the same task and work in parallel; outputs collected independently. | Brainstorming, ensemble reasoning, voting |
| **Sequential** | Output of each agent becomes input for the next in a fixed pipeline. | Step-by-step refinement, data pipelines |
| **Group chat** | A chat manager coordinates a shared conversation; agents (and optionally humans) take turns. | Maker-checker loops, collaborative review |
| **Handoff** | Control transfers dynamically between agents based on context or classification. | Customer support routing, expert escalation |
| **Magentic** | A manager agent plans, delegates, and adapts in real time using a dynamic task ledger. | Complex open-ended problems |

> **Talking point:** "All five patterns share the same core interface — you define agents, pick a builder, and call `run()`. Switching from Sequential to Concurrent is literally one class-name change. The SDK abstracts the coordination."

---

### Step 4 — Walk Through the Demo Scenario

Open [`travel-team-py/agents.py`](travel-team-py/agents.py) in VS Code.

Explain the scenario: a single raw travel request flows through three agents in sequence to produce a finished plan:

1. **Destination-Researcher** — recommends ONE destination that fits the request, with a short justification.
2. **Budget-Planner** — turns that destination into an itemized 5-day budget (flights, accommodation, food, activities, total).
3. **Itinerary-Writer** — combines the destination and budget into a friendly day-by-day itinerary.

This is a **sequential orchestration**: each agent's output is the next agent's input. Point out the sample request in [`travel-team-py/data/travel_request.txt`](travel-team-py/data/travel_request.txt) — a couple wanting a relaxed, warm, mid-range, late-spring getaway without long-haul flights from Western Europe.

> **Talking point:** "Notice the agents never coordinate explicitly. The researcher doesn't know a budget agent exists; it just answers its prompt. The pipeline wiring is what makes them a team."

---

### Step 5 — Show the Agent Creation Code

Point to the imports and client setup:

```python
import asyncio
import os
from pathlib import Path
from typing import cast
from dotenv import load_dotenv
from agent_framework import Message
from agent_framework.azure import AzureAIAgentClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

load_dotenv()
```

Show how the client authenticates and the three agents are created from it:

```python
credential = AzureCliCredential()
async with (
    AzureAIAgentClient(
        project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        model_deployment_name=os.getenv("MODEL_DEPLOYMENT_NAME"),
        credential=credential,
    ) as chat_client,
):
    destination_researcher = chat_client.as_agent(
        instructions=destination_researcher_instructions,
        name="destination_researcher",
    )
    budget_planner = chat_client.as_agent(
        instructions=budget_planner_instructions,
        name="budget_planner",
    )
    itinerary_writer = chat_client.as_agent(
        instructions=itinerary_writer_instructions,
        name="itinerary_writer",
    )
```

> **Talking point:** "All three agents come from the same `chat_client`. Each is just a different set of instructions and a name — same model, same connection. `AzureCliCredential` keeps local dev simple; in production you'd use a managed identity. The endpoint and deployment come from `.env`."

---

### Step 6 — Show the Sequential Workflow Assembly

Show the `SequentialBuilder` wiring:

```python
workflow = SequentialBuilder(
    participants=[destination_researcher, budget_planner, itinerary_writer]
).build()
```

> **Talking point:** "One line builds the entire pipeline — direct edges from researcher to planner to writer, with each agent's last message forwarded as input to the next. The order of `participants` is the order of execution. Compare that to building this by hand with queues and callbacks."

---

### Step 7 — Run the Workflow and Stream Events

Show the async execution loop and the output display:

```python
outputs: list[list[Message]] = []
async for event in workflow.run(f"Travel request: {request}", stream=True):
    if event.type == "output":
        outputs.append(cast(list[Message], event.data))

if outputs:
    for i, msg in enumerate(outputs[-1], start=1):
        name = msg.author_name or ("assistant" if msg.role == "assistant" else "user")
        print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")
```

> **Talking point:** "The `run()` method is async and event-driven. `WorkflowOutputEvent` fires when the full pipeline completes; `outputs[-1]` is the final conversation. Because each message carries `author_name`, we can see exactly which agent produced each block of text."

---

### Step 8 — Run the Demo Live

From [`travel-team-py/`](travel-team-py/) with the virtual environment active:

```powershell
python agents.py
```

You should see output similar to the following (model wording will vary):

```output
------------------------------------------------------------
01 [user]
Travel request: We are two adults looking for a relaxed 5-day getaway in late spring...
------------------------------------------------------------
02 [destination_researcher]
Valencia, Spain. Warm, dry late-spring weather, a walkable historic old town, and
city beaches reachable by tram make it an easy short-haul pick from Western Europe.
------------------------------------------------------------
03 [budget_planner]
Flights: ~$240 (2 adults, short-haul return)
Accommodation: ~$650 (5 nights, mid-range)
Food: ~$400
Activities: ~$210
Total: ~$1,500
------------------------------------------------------------
04 [itinerary_writer]
Day 1: Arrive and stroll the Barrio del Carmen old town...
Day 2: ...
...
Packing tip: light layers and comfortable walking shoes.
```

> **Talking point:** "Each stage builds on the previous one. The itinerary writer never saw the raw request — it only saw the destination and the budget. That isolation keeps each agent focused and independently testable, and it's why the final plan stays inside the budget the planner produced."

Optionally, swap the request to show the team adapt — edit [`data/travel_request.txt`](travel-team-py/data/travel_request.txt) to something like a family ski trip on a tight budget, then re-run.

---

### Step 9 — Briefly Show the Other Builder Classes

Open the relevant module units and show that switching patterns is a builder swap — the agents don't change:

```python
# Concurrent — all agents run on the same task in parallel
from agent_framework.orchestrations import ConcurrentBuilder
workflow = ConcurrentBuilder(participants=[agent1, agent2, agent3]).build()

# Group chat — a manager decides who speaks next
from agent_framework.orchestrations import GroupChatBuilder
workflow = GroupChatBuilder(participants=[maker, checker]).build()

# Magentic — a manager plans and delegates dynamically
from agent_framework.orchestrations import MagenticBuilder
workflow = MagenticBuilder(participants=[research_agent, code_agent]).build()
```

> **Talking point:** "Your agents stay the same; only the orchestration strategy changes. The Microsoft Agent Framework treats agents as pure capabilities and orchestration as a separate concern — that's what makes it easy to experiment."

---

### Cleanup

This demo creates no persistent server-side resources — the agents are defined in-process for the duration of the run. After your own exercise, remind students to:

- Delete the deployed model via the Foundry Toolkit extension (refresh **Azure Resources** → **Models** → right-click → **Delete**).
- Delete the Azure resource group to avoid ongoing charges.

---

### Summary

| Concept | Key Takeaway |
|---|---|
| Microsoft Agent Framework | Open-source SDK; provider-agnostic; supports Azure OpenAI, OpenAI, Anthropic and more |
| Agents | LLM + instructions + optional tools; created via `chat_client.as_agent()` |
| Workflows | Executors connected by edges; observable via built-in events |
| Sequential pattern | Fixed pipeline; each agent's output is the next agent's input; use `SequentialBuilder` |
| Concurrent pattern | All agents process the same task in parallel; use `ConcurrentBuilder` |
| Group chat pattern | Managed conversation with turn selection; use `GroupChatBuilder` |
| Handoff pattern | Dynamic routing based on context/classification |
| Magentic pattern | Adaptive planning manager + specialists; use `MagenticBuilder` |
| Demo scenario | Travel planning team: Destination-Researcher → Budget-Planner → Itinerary-Writer via `SequentialBuilder` |

The complete, self-contained runnable solution lives in [`travel-team-py/`](travel-team-py/).

Students will now complete the lab themselves — a different scenario (customer-feedback triage) using the same sequential orchestration pattern:
https://learn.microsoft.com/en-us/training/modules/orchestrate-semantic-kernel-multi-agent-solution/9-exercise
