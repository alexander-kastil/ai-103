# foundry-workflow-declarative — Foundry Portal Declarative Workflows (CSDL)

Authoring and publishing **portal** workflows: the visual-designer / `WorkflowAgentDefinition` path that orchestrates agents with SetVariable, Foreach, if/else routing, and SendActivity. The workflow body is **CSDL YAML** whose expressions are [Power Fx](foundry-workflow-powerfx.md).

> This is a DIFFERENT thing from [`agent-framework-workflow`](agent-framework-workflow.md), which is the Python `WorkflowBuilder` / `MagenticBuilder` SDK (code-first, in-process). If the workflow lives in the Foundry portal canvas or is published as a `WorkflowAgentDefinition`, you are here.

## When to Use

- Building a multi-agent workflow in the Foundry portal (Build → Agents → Workflows)
- Publishing a workflow programmatically via `WorkflowAgentDefinition`
- A published workflow renders as an empty canvas, or its routing never executes
- Invoking a published workflow by name from Python

## The CSDL dialect (CRITICAL — this is non-obvious)

The Foundry portal CSDL dialect is **not** the dialect shown in the Agent Framework declarative-workflow docs (learn.microsoft.com/agent-framework/workflows/declarative). They diverge exactly on the control-flow nodes:

| Logic | Agent Framework docs (DO NOT use for portal) | Foundry portal CSDL (USE THIS) |
| --- | --- | --- |
| If / Else | `kind: If` + `then:` / `else:` | `kind: ConditionGroup` + `conditions:` (list of `{condition, actions}`) + `elseActions:` |
| For-Each | `kind: Foreach` + `source:` / `itemName:` | `kind: Foreach` + `items:` / `value:` / `index:` |

Verified by exporting a portal-built workflow (Build → YAML view), 2026-06.

## The empty-canvas gotcha (HARD LESSON)

Publishing a `WorkflowAgentDefinition` whose YAML uses the **wrong dialect** (`kind: If`) is **accepted by the API without error**. At runtime it even executes the non-conditional prefix (SetVariable, Foreach, the first agent invoke), so a quick test "looks like it half-works." But the conditional subtree is **silently dropped**:

- The Foundry portal **renders the workflow as an empty canvas** (just a `Start` node + "What happens next?").
- The if/else routing and everything inside it **never runs** — no `ConditionGroup`/`If` action ever appears in the run trace.

**Always verify a published workflow by opening its portal canvas** (use `chrome-devtools` MCP to navigate to `.../build/workflows/<name>/build` and screenshot). If the canvas is empty, the dialect is wrong — do not keep editing branch property names.

**Source of truth:** build the workflow once in the portal visual designer, switch to the **YAML** view, copy that YAML verbatim, and feed it to `WorkflowAgentDefinition(workflow=...)`. Do not hand-author routing from the Agent Framework docs.

## Node reference (portal CSDL)

| `kind:` | Key fields |
| --- | --- |
| `SetVariable` | `variable:` (e.g. `Local.X`), `value:` (Power Fx) |
| `Foreach` | `items:` (collection), `value:` (loop var, e.g. `Local.CurrentApplication`), `index:` (optional), `actions:` (loop body list) |
| `ConditionGroup` | `conditions:` (list of `{condition, actions}`), `elseActions:` (optional) |
| `InvokeAzureAgent` | `agent: { name }`, `conversationId: =System.ConversationId`, `input: { messages }`, `output: { messages, responseObject, autoSend }` |
| `SendActivity` | `activity:` (Power Fx string) — surfaces text into the response |

### InvokeAzureAgent output bindings

- `messages: Local.Foo` — stores the agent's **text** output.
- `responseObject: Local.Bar` — stores the **parsed JSON object** when the agent has a `json_schema` response format. Dot into it: `=Local.Bar.confidence`.
- `autoSend: true` — surfaces the agent message into the conversation / response `output_text`.
- Agents in one workflow share `conversationId: =System.ConversationId`, so a downstream agent reads upstream output **from the conversation thread** even if its explicit `input.messages` is empty.

## Verified working skeleton (job-application triage)

`SetVariable` → `Foreach` over a Text array → screening agent (JSON output) → nested `ConditionGroup` routing → response agent + human-review fallback:

```yaml
kind: workflow
trigger:
  kind: OnConversationStart
  id: trigger_wf
  actions:
    - kind: SetVariable
      id: set_job_applications
      variable: Local.JobApplications
      value: |-
        =["Senior Backend Engineer - ...", "Junior Data Analyst - ...", "Cloud Solutions Architect - ..."]
    - kind: Foreach
      id: for_each_application
      items: =Local.JobApplications
      value: Local.CurrentApplication
      actions:
        - kind: InvokeAzureAgent
          id: invoke_screening_agent
          agent:
            name: Screening-Agent
          conversationId: =System.ConversationId
          input:
            messages: =Local.CurrentApplication
          output:
            autoSend: true
            messages: Local.ScreeningOutputText
            responseObject: Local.ScreeningOutputJson
        - kind: ConditionGroup
          id: if_confidence
          conditions:
            - condition: =Local.ScreeningOutputJson.confidence > 0.6
              id: if_confidence_true
              actions:
                - kind: ConditionGroup
                  id: if_decision
                  conditions:
                    - condition: =Local.ScreeningOutputJson.decision = "Reject"
                      id: if_decision_true
                      actions:
                        - kind: SendActivity
                          id: send_rejection
                          activity: Sending a standard rejection notice. No candidate email drafted.
                  elseActions:
                    - kind: InvokeAzureAgent
                      id: invoke_response_agent
                      agent:
                        name: Response-Agent
                      conversationId: =System.ConversationId
                      input:
                        messages: =Local.ScreeningOutputText
                      output:
                        autoSend: true
                        messages: Local.ResponseOutputText
          elseActions:
            - kind: SendActivity
              id: send_human_review
              activity: |-
                =Concat("Low confidence. Routing to a human recruiter for manual review: ", Local.CurrentApplication)
id: ""
name: <workflow-name>
description: ""
```

## Publishing (azure-ai-projects 2.x)

```python
from azure.ai.projects.models import (
    PromptAgentDefinition, PromptAgentDefinitionTextOptions,
    TextResponseFormatJsonSchema, WorkflowAgentDefinition, FoundryFeaturesOptInKeys,
)

# 1. Sub-agents first. Structured output → TextResponseFormatJsonSchema (strict).
project_client.agents.create_version("Screening-Agent", definition=PromptAgentDefinition(
    model=MODEL, instructions=SCREENING_INSTRUCTIONS,
    text=PromptAgentDefinitionTextOptions(
        format=TextResponseFormatJsonSchema(name="screening_response", schema=SCHEMA, strict=True))))

# 2. The workflow. Requires the preview opt-in feature flag.
project_client.agents.create_version(WORKFLOW_NAME,
    definition=WorkflowAgentDefinition(workflow=WORKFLOW_YAML),
    foundry_features=FoundryFeaturesOptInKeys.WORKFLOW_AGENTS_V1_PREVIEW)
```

Sub-agents referenced in `InvokeAzureAgent` must exist (publish them before the workflow).

## Invoking a published workflow by name

```python
openai_client = project_client.get_openai_client()
conversation = openai_client.conversations.create()
stream = openai_client.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": WORKFLOW_NAME, "type": "agent_reference"}},
    input="Start processing",
    stream=True,
)
for event in stream:
    if event.type == "response.completed":
        print(openai_client.responses.retrieve(event.response.id).output_text)
```

`agent_reference` by name resolves to the **published** version — a saved-but-unpublished portal workflow is not yet callable.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Portal canvas empty (just `Start`) after SDK publish | Wrong CSDL dialect (`kind: If`). Rebuild in portal, export YAML, republish that. Verify canvas via `chrome-devtools`. |
| Routing never runs; trace shows only SetVariable/Foreach/agent | Same as above — conditional subtree dropped. Use `ConditionGroup`. |
| `'.' operator cannot be used on Text values` | Power Fx type bug — see [`foundry-workflow-powerfx`](foundry-workflow-powerfx.md). |
| Agent's email/text not in `output_text` | Set `autoSend: true` on that `InvokeAzureAgent`, or add a `SendActivity` that emits the variable. |
| `agent_reference` not found at invoke | Workflow saved but not **Published**; or name mismatch. |
| Lost nodes after editing | Portal does not autosave — click **Save**. Never reload the page with unsaved changes. |
