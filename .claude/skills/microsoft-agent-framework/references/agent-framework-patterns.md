# Agent Framework Code Patterns (Python)

> **Before any SDK call, package change, or import restructuring on Agent Framework projects**: check MS Learn docs or pip constraints first. This is a hard rule — do not skip it under time pressure.

## FoundryChatClient — Key Facts

- **NOT an async context manager** — create as a plain object, no `async with`
- **One client per model tier**, shared across all agents that use the same model
- Use `model=` not `model_deployment_name=`
- Agent constructor uses keyword `client=`

```python
# Correct
client = FoundryChatClient(model="gpt-5.4-mini", credential=credential)
agent = Agent(client=client, name="MyAgent", instructions="...")

# Wrong — do not do this
async with FoundryChatClient(...) as client:  # ❌ not a context manager
    ...
agent = Agent(model_deployment_name="gpt-5.4-mini", ...)  # ❌ wrong kwarg
```

## agentserver b17 Shim (legacy only)

If a project still uses `azure-ai-agentserver-agentframework==1.0.0b17`, apply this monkey-patch **before** importing `from_agent_framework`:

```python
import agent_framework
agent_framework.BaseContextProvider = agent_framework.ContextProvider  # shim for GA rename
from azure.ai.agentserver.agentframework import from_agent_framework
```

The GA core (`1.0.x`) renamed `BaseContextProvider` → `ContextProvider`. The b17 bridge was written against the old name and breaks without this shim.

---

## Basic Agent with FoundryChatClient

```python
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

credential = AzureCliCredential()
client = FoundryChatClient(
    project_endpoint="https://your-project.services.ai.azure.com/api/projects/your-project",
    model="gpt-5.4-mini",
    credential=credential,
)

agent = Agent(
    client=client,
    name="MyAgent",
    instructions="You are a helpful assistant.",
)

result = await agent.run("Hello!")
print(result)
```

## Hosted Agent Server Mode

```python
from agent_framework import Agent, SkillsProvider
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

def get_credential():
    return (
        ManagedIdentityCredential()
        if os.getenv("MSI_ENDPOINT")
        else DefaultAzureCredential()
    )

client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_DEPLOYMENT_NAME,
    credential=get_credential(),
)

agent = Agent(
    client=client,
    name="MyAgent",
    instructions="Your system prompt here.",
    context_providers=[SkillsProvider(skill_paths=[skills_dir])],
)

# Start the hosted agent HTTP server (port 8088)
from agent_framework_foundry_hosting import ResponsesHostServer
ResponsesHostServer(agent).run()
```

## Magentic Orchestration (MagenticBuilder)

```python
from agent_framework import Agent
from agent_framework.orchestrations import MagenticBuilder

writer = Agent(name="Writer", client=client, instructions="You compose poems...")
translator = Agent(name="Translator", client=client, instructions="You translate to German...")
manager = Agent(name="MagenticManager", client=client, instructions="You coordinate the team...")

workflow = MagenticBuilder(
    participants=[writer, translator],
    manager_agent=manager,
    max_round_count=5,
    max_stall_count=2,
).build()

# CLI mode: run once
async for event in workflow.run(task, stream=True):
    ...
# Server mode: expose as hosted agent
agent = workflow.as_agent()
ResponsesHostServer(agent).run()
```

## Non-Foundry Models (OpenAIChatCompletionClient)

Use `OpenAIChatCompletionClient` with `base_url` for any OpenAI-compatible endpoint (DeepSeek, Ollama, LM Studio, vLLM, etc.):

```python
from agent_framework.openai import OpenAIChatCompletionClient

client = OpenAIChatCompletionClient(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com/v1/",
    api_key=os.environ["DEEPSEEK_API_KEY"],
)

agent = Agent(client=client, name="MyAgent", instructions="...")
```

Note: `OpenAIChatClient` uses the Responses API; most third-party providers only support Chat Completions. Use `OpenAIChatCompletionClient` for non-Foundry/non-Azure-OpenAI models.

## Sequential Workflow (WorkflowBuilder)

```python
workflow = (
    WorkflowBuilder(
        name="Writer-Reviewer",
        start_executor=writer,
        output_executors=[writer, reviewer],
    )
    .add_edge(writer, reviewer)
    .build()
)

agent = workflow.as_agent()
response = await agent.run("Optimize this text...")
```

## Agents vs Workflows Decision

| Use an Agent when | Use a Workflow when |
|---|---|
| The task is open-ended or conversational | The process has well-defined steps |
| You need autonomous tool use and planning | You need explicit control over execution order |
| A single LLM call (possibly with tools) suffices | Multiple agents or functions must coordinate |

If you can write a function to handle the task, do that instead of using an AI agent.
