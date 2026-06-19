# agent-framework-workflow — Agent Workflow Authoring (code-first SDK)

> **Scope:** this is the Python **`WorkflowBuilder` / `MagenticBuilder` SDK** — in-process, code-first orchestration. If you are building a workflow in the **Foundry portal canvas** or publishing a **`WorkflowAgentDefinition`** (CSDL YAML with `SetVariable` / `Foreach` / `ConditionGroup` / Power Fx), use [`foundry-workflow-declarative`](foundry-workflow-declarative.md) and [`foundry-workflow-powerfx`](foundry-workflow-powerfx.md) instead. Mixing the two dialects is the classic failure: a portal workflow authored from these SDK docs publishes to an empty canvas.

## When to Use

- Adding a new agent to a WorkflowBuilder or MagenticBuilder pipeline
- Changing workflow topology (linear → branching, sequential → concurrent)
- Adding HITL (human-in-the-loop) gates
- Configuring retry/revision logic
- Wiring `SkillsProvider` for per-agent skills

## Workflow Patterns

### Sequential Chain (WorkflowBuilder)

```python
workflow = (
    WorkflowBuilder(
        name="OptimizeWorkflow",
        start_executor=writer,
        output_executors=[writer, reviewer],
    )
    .add_edge(writer, reviewer)
    .build()
)
```

### Dynamic Coordination (MagenticBuilder)

```python
workflow = MagenticBuilder(
    participants=[writer, translator],
    manager_agent=manager,
    max_round_count=5,
    max_stall_count=2,
).build()

agent = workflow.as_agent()
```

### Conditional Branching

```python
workflow = (
    WorkflowBuilder(...)
    .add_switch_case_edge_group(reviewer, [
        Case(condition=is_revise, target=writer),
        Default(target=publisher),
    ])
    .build()
)
```

### Adding a New Agent

1. Define the agent with `Agent(client, name=..., instructions=..., tools=..., context_providers=...)`
2. Add its skill directory under `skills/<agent-name>/`
3. Wire it into the builder with `.add_edge()`
4. Add to participants list (Magentic) or output_executors (Workflow)
5. If needed, update the operation router

## Example: `<agent-project>`

A typical project uses `WorkflowBuilder` with an operation router that dispatches to sub-flows. See `src/<agent-project>/main.py` for the full workflow topology.
