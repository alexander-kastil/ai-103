# Discover Azure AI Agents with A2A

https://learn.microsoft.com/en-us/training/modules/discover-agents-with-a2a/

---

## Instructor Demo Guide

This demo shows how to build a multi-agent **podcast-episode planning** system using the Agent-to-Agent (A2A) protocol with Microsoft Foundry **prompt agents**. Two specialized remote agents — a **segment agent** that drafts an episode segment breakdown and a **title agent** that proposes catchy episode titles — each run as their own HTTP server and publish an Agent Card. A **routing (host) agent** discovers them through those cards and delegates podcast-planning requests, composing a title-then-segments workflow without any tight coupling between the agents.

Each underlying agent is a Foundry **prompt agent** (Azure AI Projects 2.x): it is created with `project.agents.create_version(...)` using a `PromptAgentDefinition`, and conversations run through the **Responses API** on the project's OpenAI client (`project.get_openai_client()`) instead of the older Assistants threads/messages/runs.

A complete, runnable solution lives next to this guide in [`podcast-a2a-py/`](podcast-a2a-py/) — you don't need to clone the lab repo to run it.

**Estimated time:** 30–40 minutes

---

### Prerequisites

- Python 3.10+ on the PATH (verified on 3.12)
- An active Azure subscription with a Foundry project and two models deployed: `gpt-5.4` (title and segment agents) and `gpt-5.2` (routing agent, see note below)
- Signed in to Azure: `az login` (the demo uses `DefaultAzureCredential`)
- Demo working directory: [`podcast-a2a-py/`](podcast-a2a-py/)

This demo's Foundry project endpoint:

```
https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos
```

### One-time setup

From the [`podcast-a2a-py/`](podcast-a2a-py/) folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit .env if your deployment name differs
az login
```

`.env.example` already points `PROJECT_ENDPOINT` at the demo project above. Set `MODEL_DEPLOYMENT_NAME` (title and segment agents) and `ROUTING_MODEL_DEPLOYMENT_NAME` (routing agent) to match your deployments. The three agent ports are pre-configured:

| Variable | Value | Agent |
|---|---|---|
| `TITLE_AGENT_PORT` | `10007` | Title agent (remote) |
| `SEGMENT_AGENT_PORT` | `10008` | Segment agent (remote) |
| `ROUTING_AGENT_PORT` | `10009` | Routing / host agent |

---

### Step 1 — Introduce the A2A protocol and the scenario

Open the module introduction page and orient students to the scenario: a podcast production workflow where two specialized agents collaborate to plan an episode.

Draw or display the three-agent architecture:

```
User
 └── routing_agent  (orchestrator / host)
      ├── title_agent    (proposes catchy episode titles)
      └── segment_agent  (drafts the episode segment breakdown)
```

> **Talking point:** "Each agent runs as its own HTTP server. The routing agent doesn't know how the other agents work internally — it just discovers their capabilities through an Agent Card, like reading a business card before making a call. Swap the title agent for a different implementation and the routing agent never notices."

---

### Step 2 — Explore the file layout

In VS Code, open [`podcast-a2a-py/`](podcast-a2a-py/) and point out the structure — each remote agent is a self-contained package:

```
podcast-a2a-py/
├── segment_agent/
│   ├── agent.py            # the Foundry prompt agent that drafts segment breakdowns
│   ├── agent_executor.py   # A2A executor bridging the protocol to the agent
│   └── server.py           # Starlette + Uvicorn server, publishes the Agent Card
├── title_agent/
│   ├── agent.py            # the Foundry prompt agent that proposes episode titles
│   ├── agent_executor.py
│   └── server.py
├── routing_agent/
│   ├── agent.py            # discovers remote agents, delegates via send_message
│   └── server.py           # FastAPI host exposing /message to the client
├── client.py               # console client that posts prompts to the routing agent
├── run_all.py              # launches all three servers, then runs the client
├── requirements.txt
└── .env.example
```

> **Talking point:** "Notice the title and segment agents are mirror images of each other — same three-file shape. That uniformity is the point of A2A: every agent looks the same from the outside regardless of what it does inside."

---

### Step 3 — Explore the Agent Card and skills

Open [`segment_agent/server.py`](podcast-a2a-py/segment_agent/server.py) and walk through the skill definition:

```python
skills = [
    AgentSkill(
        id='generate_episode_segments',
        name='Generate Episode Segments',
        description='Generates a podcast episode segment breakdown based on a topic',
        tags=['segments', 'podcast'],
        examples=['Can you give me a segment breakdown for this episode?'],
    ),
]
```

Then show the Agent Card that wraps those skills:

```python
agent_card = AgentCard(
    name='AI Foundry Segment Agent',
    description='An intelligent podcast segment planner agent powered by Azure AI Foundry. '
                'I can help you break a podcast episode into clear segments.',
    url=f'http://{host}:{port}/',
    version='1.0.0',
    default_input_modes=['text'],
    default_output_modes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=skills,
)
```

Point out that the Agent Card is automatically served at `/.well-known/agent-card.json` — this is the discovery endpoint any client or routing agent fetches first.

> **Talking point:** "The Agent Card is a contract. Any agent or client that wants to call this agent fetches this JSON document first to learn what it can do and where it lives. This is what makes A2A agents discoverable without hard-coding dependencies."

---

### Step 4 — Explore the agent executor

Open [`segment_agent/agent_executor.py`](podcast-a2a-py/segment_agent/agent_executor.py) and explain the two responsibilities: `execute` and `cancel`.

Walk through the request-handling flow inside `_process_request`:

```python
# 1. Create or reuse the underlying Azure AI Agent
agent = await self._get_or_create_agent()

# 2. Signal that work is starting
await task_updater.update_status(
    TaskState.working,
    message=new_agent_text_message(
        'Segment Agent is processing your request...', context_id=context_id
    ),
)

# 3. Run the conversation against the Azure AI Agent
responses = await agent.run_conversation(user_message)

# 4. Mark the task complete with the final response
final_message = responses[-1] if responses else 'Task completed.'
await task_updater.complete(
    message=new_agent_text_message(final_message, context_id=context_id)
)
```

> **Talking point:** "The executor is the bridge between the A2A protocol layer and the Foundry prompt agent. It translates an incoming A2A task into a Responses API call against the agent, runs it, and feeds results back through the event queue with `TaskUpdater` — so the calling agent gets status updates as the work progresses, not just a final blob at the end."

---

### Step 5 — Show the underlying Foundry prompt agent

Open [`title_agent/agent.py`](podcast-a2a-py/title_agent/agent.py) and show how the project client is created and the prompt agent is registered with `create_version`:

```python
self.project = AIProjectClient(
    endpoint=os.environ['PROJECT_ENDPOINT'],
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True
    )
)
self.openai = self.project.get_openai_client()

self.agent = self.project.agents.create_version(
    agent_name='podcast-title-agent',
    definition=PromptAgentDefinition(
        model=os.environ['MODEL_DEPLOYMENT_NAME'],
        instructions="""
        You are a helpful podcast production assistant.
        Given a topic the user wants to cover in an episode, suggest a single clear and catchy podcast episode title.
        Keep it punchy and listener-friendly, ideally under 10 words.
        """,
    ),
)
```

Then show how a turn runs through the **Responses API** — no threads, messages, or runs:

```python
response = self.openai.responses.create(
    input=user_message,
    extra_body={"agent_reference": {"name": 'podcast-title-agent', "type": "agent_reference"}},
)
title = response.output_text
```

> **Talking point:** "This is the new Foundry prompt-agent pattern from Azure AI Projects 2.x. The agent definition (model + instructions + tools) is versioned in Foundry with `create_version`, and each turn is a single `responses.create` call that returns the assistant text directly via `output_text` — no thread to create, no run to poll. The segment agent is the same pattern with different instructions."

---

### Step 6 — Explore the routing (host) agent

Open [`routing_agent/agent.py`](podcast-a2a-py/routing_agent/agent.py). On startup it fetches each remote agent's Agent Card:

```python
card_resolver = A2ACardResolver(client, address)
card = await card_resolver.get_agent_card()
remote_connection = RemoteAgentConnections(agent_card=card, agent_url=address)
self.remote_agent_connections[card.name] = remote_connection
self.cards[card.name] = card
```

Then show how it calls a remote agent in `send_message`:

```python
# 1. Look up the A2A client for the target agent by name
client = self.remote_agent_connections[agent_name]

# 2. Build the A2A message payload
payload: dict[str, Any] = {
    'message': {
        'role': 'user',
        'parts': [{'kind': 'text', 'text': task}],
        'messageId': message_id,
    },
}

# 3. Wrap in a SendMessageRequest
message_request = SendMessageRequest(
    id=message_id, params=MessageSendParams.model_validate(payload)
)

# 4. Send to the remote agent
send_response: SendMessageResponse = await client.send_message(
    message_request=message_request
)
```

The routing agent registers `send_message` on its prompt agent as a **`FunctionTool`** in the `PromptAgentDefinition`, and its instructions tell it to get a title first, then pass that title to the segment agent so the segments match the title. Each turn runs a Responses tool-call loop: the model emits `function_call` output items, the agent runs `send_message` and feeds the results back as `function_call_output` items on the same conversation, repeating until the model returns a final answer.

> **Model caveat:** not every Foundry model supports the **Function** tool. `gpt-5.4` does **not** (the title and segment agents use no tools, so they run fine on it), so the routing agent is pointed at a separate `ROUTING_MODEL_DEPLOYMENT_NAME` (default `gpt-5.2`, which is Function-capable). Confirm tool support for your model and region in [Tool support by region and model](https://learn.microsoft.com/azure/foundry/agents/concepts/tool-best-practice#tool-support-by-region-and-model).

> **Talking point:** "The routing agent already fetched each remote agent's Agent Card on startup, so by the time it calls `send_message` it knows the endpoint URL and capabilities. The title-then-segments workflow is orchestrated here — the model decides which agent to call by emitting a `function_call`, our code runs the actual A2A HTTP call, and submits the result back as a `function_call_output` so the model can continue. The conversation object keeps context across those turns automatically."

---

### Step 7 — Run the multi-agent system

From [`podcast-a2a-py/`](podcast-a2a-py/) with the virtual environment active and `az login` complete:

```powershell
python run_all.py
```

`run_all.py` starts all three servers (title on 10007, segment on 10008, routing on 10009), waits for each `/health` endpoint to report ready, then launches the console client. Wait until the prompt appears, then enter:

```
Plan a podcast episode about the rise of small language models. I need a catchy title and a segment breakdown.
```

Expected output (abridged — exact wording varies by model run):

```
🚀 Starting title_agent_server on port 10007
✅ title_agent_server is healthy and ready!
🚀 Starting segment_agent_server on port 10008
✅ segment_agent_server is healthy and ready!
🚀 Starting routing_agent_server on port 10009
✅ routing_agent_server is healthy and ready!
Enter a prompt for the podcast planning agent. Type 'quit' to exit.
User: Plan a podcast episode about the rise of small language models. I need a catchy title and a segment breakdown.
Agent: Title: "Small Models, Big Impact"

Segment breakdown:
1. Cold open — a surprising small-model benchmark result
2. Why small language models are suddenly everywhere
3. On-device and edge use cases worth caring about
4. Trade-offs: cost, latency, and capability
5. Where this goes next — predictions for the year
6. Wrap-up and a question for listeners
```

> **Talking point:** "One user message produced two delegated calls. The title agent and segment agent have no knowledge of each other — the routing agent discovered them via their Agent Cards and composed the workflow. This is the key value of A2A: modular, independently deployable agents that collaborate without tight coupling."

Enter `quit` to exit the client; `run_all.py` then shuts the three servers down. You can also run `deactivate` to leave the virtual environment.

---

### Step 8 — Point to the discovery endpoint (optional live demo)

While the servers are running, open a browser or use `curl` to show an Agent Card live:

```
http://localhost:10008/.well-known/agent-card.json
```

> **Talking point:** "Any client or routing agent in the world — given just this URL — can discover what this agent does and where it lives, with zero prior configuration. That's standardized agent discovery in action."

---

### Demo resources

This demo was verified end-to-end against the following pre-created Azure resources.

| Resource | Name | Endpoint / value |
|---|---|---|
| Foundry resource | `ai-103-demos-resource` | `https://ai-103-demos-resource.services.ai.azure.com` |
| Foundry project | `ai-103-demos` | `https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos` |
| Model deployment (title + segment agents) | `gpt-5.4` | `MODEL_DEPLOYMENT_NAME` |
| Model deployment (routing agent, Function-capable) | `gpt-5.2` | `ROUTING_MODEL_DEPLOYMENT_NAME` |

Three prompt agents are created in the project on first run and persist between runs: `podcast-title-agent`, `foundry-segment-agent`, `podcast-routing-agent`.

### Permissions required

The signed-in identity (`az login`, used via `DefaultAzureCredential`) needs **Azure AI User** on the Foundry project to create agent versions and call the Responses API.

### Errors encountered and fixes applied

| Symptom | Cause | Fix |
|---|---|---|
| `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'` on startup | Windows console / piped stdout defaults to `cp1252`, which cannot encode the status emojis | `run_all.py` and `client.py` call `sys.stdout.reconfigure(encoding="utf-8")`; server subprocesses are spawned with `encoding="utf-8"`, `errors="replace"`, and `PYTHONIOENCODING=utf-8` |
| Process exits non-zero with no `Goodbye!` or shutdown messages | On Windows, `CTRL_BREAK_EVENT` was sent to subprocesses created in the parent's own process group, killing `run_all.py` before it could shut the servers down cleanly | Spawn servers with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` on Windows so the break signal reaches only the child group |

After these fixes the run exits with code `0`, prints `Goodbye!`, and all three uvicorn servers report `Application shutdown complete`.

### Cleanup

The agents created in the Foundry project persist between runs. After the demo, delete the Azure resource group in the portal to stop billing on the deployed model and project resources. Remind students to do the same after their own exercise.

---

### Summary

| Concept | What it does | Where |
|---|---|---|
| **Agent Skill** | Declares a specific capability (id, name, description, examples) | `*/server.py`, Step 3 |
| **Agent Card** | Discovery document served at `/.well-known/agent-card.json`; describes skills and endpoint | `*/server.py`, Step 3 |
| **Agent Executor** | Bridges the A2A protocol layer to the underlying Foundry prompt agent; handles `execute` and `cancel` | `*/agent_executor.py`, Step 4 |
| **Underlying Foundry agent** | Foundry prompt agent (Azure AI Projects 2.x) — `create_version` + Responses API | `*/agent.py`, Step 5 |
| **A2A Server** | Starlette + Uvicorn host that exposes the Agent Card and routes requests to the executor | `*/server.py` |
| **Routing Agent** | Host that fetches Agent Cards, selects the right agent, and sequences tasks via `send_message` | `routing_agent/agent.py`, Step 6 |
| **Client** | Posts prompts to the routing agent and prints the composed response | `client.py`, Step 7 |
| **End-to-end test** | Podcast planner: one prompt, title-then-segments delegated across two remote agents | Step 7 |

> The complete runnable solution for this demo lives in [`podcast-a2a-py/`](podcast-a2a-py/). Students complete the matching lab — a **blog-content** A2A solution (title agent + outline agent + routing agent) — on their own afterward.
