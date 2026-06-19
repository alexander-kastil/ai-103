# Agent Framework Orchestration Patterns

Real-world orchestration patterns extracted from WorkflowBuilder and MagenticBuilder projects. Use these as reference architectures when designing agent workflows.

## Pattern Decision Tree

| You need… | Use… | Example |
|---|---|---|
| Fixed execution order, known steps | `WorkflowBuilder` | content-creator-team |
| Manager dynamically chooses next agent | `MagenticBuilder` | maf-smoke-test |

---

## WorkflowBuilder Patterns (Fixed Pipelines)

Source: `src/<agent-project>/main.py`

### 1. Operation Router (Entry Agent + Dispatch)

A single entry agent classifies the input, then `add_switch_case_edge_group` dispatches to specialized sub-flows.

```python
workflow = (
    WorkflowBuilder(
        name="ContentCreator",
        start_executor=router_agent,
        output_executors=[path_a_output, path_b_output, fallback],
        max_iterations=15,
    )
    .add_switch_case_edge_group(router_agent, [
        Case(condition=routes_to("optimize"),       target=writer_opt),
        Case(condition=routes_to("translate"),      target=writer_tr),
        Case(condition=routes_to("create-article"), target=researcher),
        Default(target=not_implemented),
    ])
    .build()
)
```

**Key decisions:**
- Router agent returns structured JSON (e.g. `{"route": "create-article", ...}`)
- Condition functions parse JSON and match on a field: `routes_to("optimize")` checks `json.loads(...).get("route") == "optimize"`
- Always include a `Default` fallback for unrecognized routes
- `max_iterations` caps total workflow steps as a safety net

### 2. Feedback Loop (Revise Cycle)

A conditional edge loops back for quality iterations, with `max_iterations` preventing infinite loops.

```python
workflow = (
    WorkflowBuilder(..., max_iterations=15)
    .add_edge(writer, reviewer)
    .add_edge(reviewer, writer, condition=is_revise)    # ← loopback
    .build()
)
```

The condition function checks the reviewer output:

```python
def is_revise(data: Any) -> bool:
    try:
        parsed = json.loads(_get_text(data))
        return parsed.get("verdict") == "REVISE" or parsed.get("overall") == "REVISE"
    except (json.JSONDecodeError, ValueError):
        return False
```

**Key decisions:**
- Condition on `add_edge()` creates the loopback — no edge means the workflow terminates
- Reviewer output is structured JSON with `verdict` or `overall` field
- `max_iterations` prevents runaway revise cycles
- Revision is bounded: "Max 2 revision rounds" in reviewer instructions

### 3. Concurrent Fan-Out

A single agent's output fans to multiple downstream agents running in parallel.

```python
workflow = (
    WorkflowBuilder(...)
    # ... up to reviewer_article ...
    .add_edge(reviewer_article, writer_article, condition=is_revise)  # feedback loop
    .add_edge(reviewer_article, publisher)                             # parallel fan-out
    .add_edge(reviewer_article, translator)                            # parallel fan-out
    .build()
)
```

When the reviewer approves, both Publisher and Translator receive the output concurrently.

**Key decisions:**
- Multiple edges from the same source run in parallel
- Use when outputs are independent (publisher creates social posts, translator localizes)
- No explicit synchronization needed — both complete before the workflow finishes

### 4. Multi-Tier Model Strategy

Different agents use different model deployments based on task complexity.

```python
ROUTER_MODEL  = "gpt-5-nano"        # classification only
UTILITY_MODEL = "gpt-5-mini"        # rewrites, translation
PREMIUM_MODEL = "claude-sonnet-4-6" # research, article writing/review

router_client  = FoundryChatClient(project_endpoint=..., model=ROUTER_MODEL,  credential=...)
utility_client = FoundryChatClient(project_endpoint=..., model=UTILITY_MODEL, credential=...)
premium_client = FoundryChatClient(project_endpoint=..., model=PREMIUM_MODEL, credential=...)

router_agent   = Agent(router_client,  name="ContentCreator", ...)
writer_opt     = Agent(utility_client, name="Writer-Optimize", ...)
researcher     = Agent(premium_client, name="Researcher",      ...)
```

**Key decisions:**
- One `FoundryChatClient` per model tier, shared across agents on the same tier
- Cheapest model for routing (classification only)
- Mid-tier for text transformation (optimize, translate)
- Premium model for quality-critical work (research, article writing)
- Per-tier clients also enable per-tier cost tracking and rate limits

### 5. Agent Naming Convention

Suffix agent names with their path when the same role appears in multiple sub-flows.

```
Writer-Optimize      # optimize path
Writer-Translate     # translate path
Writer-Article       # create-article path
Reviewer-Optimize    # optimize path
Reviewer-Translate   # translate path
Reviewer-Article     # create-article path
```

**Key decisions:**
- Same role, different sub-flows → suffix with path name
- Different roles in the same sub-flow → no suffix needed (Researcher, Publisher, Translator)
- Agent name is used in `output_executors` list and edge wiring

---

## MagenticBuilder Patterns (Dynamic Coordination)

Source: `src/<smoke-test-project>/main.py`

### 6. Magentic Manager

A manager agent dynamically decides which participants to invoke and in what order.

```python
manager_agent = Agent(
    name="MagenticManager",
    instructions=(
        "You coordinate a small creative team. Your team has two specialists:\n"
        "- Writer: composes original 200-word poems\n"
        "- Translator: translates English text into fluent German\n\n"
        "When given a poem topic:\n"
        "1. First delegate to Writer to compose the poem.\n"
        "2. Then delegate to Translator to translate the poem to German.\n"
        "Return both the English original and the German translation as the final output."
    ),
    client=client,
)

workflow = MagenticBuilder(
    participants=[writer, translator],
    intermediate_outputs=True,
    manager_agent=manager_agent,
    max_round_count=5,
    max_stall_count=2,
    max_reset_count=1,
).build()
```

**Key decisions:**
- Manager instructions explicitly list available participants and their capabilities
- `intermediate_outputs=True` exposes each participant's output in the stream
- Safety limits: `max_round_count`, `max_stall_count`, `max_reset_count`
- Participants are unaware of each other — only the manager has global context

### 7. Streamed Output with Event Routing

Stream workflow events and route by event type for structured display.

```python
async for event in workflow.run(task, stream=True):
    if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
        if event.executor_id != last_executor:
            print(f"[{event.executor_id}] ", end="", flush=True)
            last_executor = event.executor_id
        print(event.data, end="", flush=True)

    elif event.type == "magentic_orchestrator":
        data = event.data
        print(f"\n--- Orchestrator: {data.event_type.name} ---", flush=True)
```

**Key decisions:**
- `stream=True` on `workflow.run()` for real-time output
- `event.type == "output"` with `AgentResponseUpdate` for participant output
- `event.type == "magentic_orchestrator"` for manager decisions (which participant, what task)
- Track `executor_id` to print agent name headers only when the speaker changes

### 8. Dual-Mode Entry Point (CLI + Server)

Same workflow usable as both a CLI test tool and a hosted agent.

```python
async def main():
    if "--cli" in sys.argv:
        # Local smoke test: run once
        async for event in workflow.run(task, stream=True):
            ...  # print output
    else:
        # Server mode: expose as hosted agent on port 8088
        agent = workflow.as_agent()
        from agent_framework_foundry_hosting import ResponsesHostServer
        ResponsesHostServer(agent).run()
```

**Key decisions:**
- `workflow.as_agent()` wraps any WorkflowBuilder or MagenticBuilder result into an `Agent`
- `ResponsesHostServer(agent).run()` starts the HTTP server on port 8088
- `--cli` flag toggles between modes
- Same agent object — no code duplication between test and production

---

## Choosing Between Patterns

| Pattern | When to use |
|---|---|
| Operation Router | Unknown input type, must classify first |
| Feedback Loop | Quality gate with revision cycles |
| Concurrent Fan-Out | Independent downstream tasks from one output |
| Multi-Tier Models | Task complexity varies across agents |
| Magentic Manager | Task order unknown in advance, manager decides dynamically |
| Dual-Mode Entry | Need both local testing and server deployment from same code |

## Anti-Patterns to Avoid

- **MagenticBuilder for known steps**: If you know the exact order, use WorkflowBuilder — it's faster and more predictable
- **Single model tier for everything**: Routing and quality writing have very different model needs
- **No max_iterations on feedback loops**: Infinite loops are always possible with LLM outputs
- **Hardcoding model names**: Use env vars with sensible defaults so deployers can swap without code changes
