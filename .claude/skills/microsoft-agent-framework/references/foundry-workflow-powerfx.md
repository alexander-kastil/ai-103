# foundry-workflow-powerfx — Power Fx for Foundry Declarative Workflows

Power Fx is the expression language inside Foundry **portal/declarative** workflows (CSDL YAML). It governs every `condition:`, `value:`, `input.messages:`, and `activity:` field. This is NOT the Python `WorkflowBuilder` SDK — see [`foundry-workflow-declarative`](foundry-workflow-declarative.md) for the node structure that hosts these expressions.

## When to Use

- Writing a `condition:` for a ConditionGroup (if/else) branch
- Setting a `SetVariable` value, an agent `input.messages`, or a `SendActivity` text
- Debugging a workflow that fails with a Power Fx type error
- Accessing a field from a JSON object an agent returned

## The `=` prefix rule

- A value starting with `=` is **evaluated as an expression**: `=Local.Count + 1`, `=["a", "b"]`.
- A value with no `=` is a **literal**: `Hello` is the string "Hello"; `42` is the number 42.
- Forgetting `=` is the most common bug: `["a","b"]` (no `=`) is stored as the literal text `["a","b"]`, not a 2-element array, so a downstream Foreach iterates one string.

## Variable scopes

| Namespace | Access | Notes |
| --- | --- | --- |
| `Local.*` | read/write | Workflow-local variables you create (SetVariable, agent output bindings, Foreach loop var) |
| `System.*` | read-only | `System.ConversationId`, `System.LastMessage`, `System.Timestamp` |
| `Workflow.Inputs.*` | read-only | Inputs passed to the workflow |
| `Workflow.Outputs.*` | read/write | Values returned from the workflow |
| `Agent.*` | read-only | Results from agent invocations |

## Operators

| Operator | Meaning | Example |
| --- | --- | --- |
| `=` | **equality** (NOT `==`) | `=Local.J.decision = "Reject"` |
| `<>` | not equal | `=Local.status <> "deleted"` |
| `<` `>` `<=` `>=` | numeric comparison | `=Local.J.confidence > 0.6` |
| `+ - * /` | arithmetic | `=Local.price + Local.tax` |

String equality with `=` is exact and case-sensitive. Use `=` for equality in conditions — `==` is not Power Fx and fails.

## Core functions

- **Concat** — join strings: `=Concat("Review: ", Local.CurrentApplication)`
- **If** — inline conditional value: `=If(Local.n > 0, "some", "none")`
- **And / Or / Not** — `=And(Local.conf > 0.6, Not(IsBlank(Local.text)))`
- **IsBlank** — empty/undefined check: `=IsBlank(Workflow.Inputs.email)`
- **Text() / Value()** — convert number→text / text→number (fixes "Type mismatch")

## Arrays vs records (and the `.` operator trap)

This single distinction caused the most painful failures in practice.

- `=["a", "b", "c"]` is a single-column table of **Text** values.
- `=Table({field: "x"}, {field: "y"})` is a table of **records**.

When a `Foreach` iterates a plain **text array**, each loop value (e.g. `Local.CurrentApplication`) is a **Text scalar**. Accessing a field on it fails:

```
Error 24-36: The '.' operator cannot be used on Text values.
```

Rules:
- `Local.CurrentApplication` (Text from a `["..."]` array) → use it directly. **Never** write `Local.CurrentApplication.application`.
- To get a record you can dot into, bind an agent's JSON output to `responseObject`:
  ```yaml
  output:
    responseObject: Local.ScreeningOutputJson   # parsed object (agent has a json_schema response format)
  ```
  Then `=Local.ScreeningOutputJson.confidence` and `=Local.ScreeningOutputJson.decision = "Reject"` work — no `ParseJSON()` needed.

## Quick reference: the verified job-screening conditions

```yaml
# Confidence gate (number compare on a responseObject field)
condition: =Local.ScreeningOutputJson.confidence > 0.6

# Decision gate (text equality with single =)
condition: =Local.ScreeningOutputJson.decision = "Reject"

# Human-review message (Concat on a Text loop var — no dot access)
activity: |-
  =Concat("Low confidence. Routing to a human recruiter for manual review: ", Local.CurrentApplication)

# Seed array (note the = and that items are plain Text, so the loop var is Text)
value: =["Senior Backend Engineer - ...", "Junior Data Analyst - ...", "Cloud Solutions Architect - ..."]
```

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `The '.' operator cannot be used on Text values` | Dotting into a Text scalar. Remove the `.field`, or bind agent JSON to `responseObject` and dot into that. |
| Foreach runs once over the whole string | Value missing `=` (stored as literal text) or the source isn't an array. |
| `Name isn't valid` | Missing scope prefix. Use `Local.` / `System.` / `Workflow.Inputs.`. |
| `Type mismatch` | Wrap with `Text()` or `Value()` to match expected type. |
| Equality never matches | Used `==`. Power Fx equality is a single `=`. |
