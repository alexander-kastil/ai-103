# Build agent-driven workflows using Microsoft Foundry

https://learn.microsoft.com/en-us/training/modules/build-agent-workflows-microsoft-foundry/

---

## Instructor Demo Guide

This demo shows students how to build a multi-agent **job-application screening triage** workflow in the Microsoft Foundry portal — using the visual designer to connect a For-Each loop, a Screening-Agent with structured JSON output, conditional routing by confidence and decision, and a Response-Agent that drafts candidate emails — then invoking the finished workflow from Python code.

A complete, runnable invoker lives next to this guide in [`workflow-demo-py/`](workflow-demo-py/) — you don't need to clone the lab repo to run the code-integration portion.

**Estimated time:** 30–40 minutes

### Prerequisites

- Azure subscription with a Microsoft Foundry project provisioned and a model deployed (e.g., `gpt-5.4`)
- Microsoft Foundry portal open at `https://ai.azure.com` with the **New Foundry** toggle enabled
- A Python environment with `azure-ai-projects` installed (for the code-integration portion)
- Familiarity with creating and configuring AI agents in Foundry (covered in earlier modules)

This demo's Foundry project endpoint:

```
https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos
```

---

### Step 1 — Orient students to the workflow canvas

1. In the Foundry portal, navigate to **Build > Agents > Workflows**.
2. Click **Create > Blank workflow**.
3. Name it `Contoso-Job-Application-Triage` and save.
4. Point out the canvas structure: nodes appear in a left-to-right execution order; connections between nodes define the control flow.

> **Talking point:** "A workflow is a sequence of connected nodes. Unlike a single agent, a workflow lets us combine multiple agents, control logic, and human checkpoints into one orchestrated process. Every workflow starts with a trigger and ends with an End node."

5. Briefly click the **+** button to show the node-type menu without adding anything yet. Name the main categories:
   - **Invoke** — calls an AI agent
   - **Flow** — If/Else, For Each, Go To
   - **Data transformation** — Set Variable, Parse Value
   - **Basic chat** — send/receive messages from the user
   - **End** — marks workflow completion

---

### Step 2 — Create the job-applications variable

1. Add a **Set Variable** (Data transformation) node.
2. Name the variable `Local.JobApplications`.
3. Paste in a small list of three sample applications:
   - `"Senior Backend Engineer — 8 years Python/Go, led a 6-person team, ex-FAANG, strong system-design portfolio."`
   - `"Junior Data Analyst — recent bootcamp grad, no commercial experience, solid SQL exercises, eager to learn."`
   - `"Cloud Solutions Architect — 12 years experience but resume is vague on specifics, no certifications listed, gaps unexplained."`
4. Save.

> **Talking point:** "We're seeding the workflow with three job applications. In a real solution this variable would be populated from an applicant-tracking system, a queue, or a form submission — but using a hard-coded list lets us test the full execution path right now."

---

### Step 3 — Add a For-Each loop

1. Add a **For Each** (Flow) node after the Set Variable node.
2. Set the **Items** field to `Local.JobApplications`.
3. Set the loop variable name to `CurrentApplication`.

> **Talking point:** "The For-Each node lets us apply the same set of actions to every item in a list without duplicating nodes. At runtime Foundry iterates the loop body once per application — this is the Power Fx `ForAll` pattern applied to a workflow."

---

### Step 4 — Add the Screening Agent

1. Inside the For-Each loop, add an **Invoke agent** node.
2. Click **Create new agent** and name it `Screening-Agent`.
3. Write the system instructions:
   > "You are a job-application screener. Classify each application into exactly one of three decisions: **Advance** (strong fit, clear evidence of required skills and experience), **Reject** (clearly under-qualified or mismatched), or **NeedsReview** (promising but ambiguous, missing details, or a borderline call). Provide a confidence score from 0 to 1. Respond only with the JSON schema provided. Do not discriminate on protected characteristics; evaluate skills and experience only."
4. Under **Details > Response format**, define a JSON schema with three properties:
   - `applicant_summary` (string)
   - `decision` (string — one of Advance, Reject, NeedsReview)
   - `confidence` (number between 0 and 1)
5. Set the **Input** to `Local.CurrentApplication`.
6. In **Action settings**, store the output:
   - Message output → `ScreeningOutputText`
   - JSON object output → `ScreeningOutputJson`
7. Save.

> **Talking point:** "Structured output is the key enabler here. By forcing the agent to return a JSON object with a known schema, later nodes can reliably read `ScreeningOutputJson.decision` and `ScreeningOutputJson.confidence` using Power Fx expressions — no text parsing needed."

The JSON schema you enter in the **Add response format** pane:

```json
{
  "name": "screening_response",
  "schema": {
    "type": "object",
    "properties": {
      "applicant_summary": { "type": "string" },
      "decision": { "type": "string" },
      "confidence": { "type": "number" }
    },
    "additionalProperties": false,
    "required": ["applicant_summary", "decision", "confidence"]
  },
  "strict": true
}
```

---

### Step 5 — Add confidence-based routing (human-in-the-loop)

1. After the Screening Agent node, add an **If/Else** (Flow) node.
2. Set the condition to: `Local.ScreeningOutputJson.confidence > 0.6`
3. In the **Else** branch (low confidence), add a **Basic chat — Deliver a message** node with the text:
   > "The application screening has low confidence. Routing to a human recruiter for manual review: \"{Local.CurrentApplication}\""

> **Talking point:** "This is the human-in-the-loop pattern. When the agent isn't confident enough, we surface that uncertainty instead of silently advancing or rejecting a candidate. Hiring decisions are high-stakes — a borderline confidence score is exactly where you want a human in the loop. Foundry can also pause and wait for a human response with additional message-and-wait nodes."

---

### Step 6 — Route by decision

1. In the **If** branch (high confidence), add a second **If/Else** node.
2. Set the condition to: `Local.ScreeningOutputJson.decision = "Reject"`
3. In the **If** branch (Reject), add a **Basic chat — Deliver a message** node:
   > "Sending a standard rejection notice. No candidate email drafted."
4. Leave the **Else** branch open for the next step.

> **Talking point:** "Sequential If/Else nesting is how we build a decision tree. The first split is on confidence, the second on the decision. Notice we're reading structured fields from `ScreeningOutputJson` — that's why we defined the JSON schema on the agent. Rejections take a short, standardized path; everything else gets a personalized email."

---

### Step 7 — Add the Response Agent

1. In the **Else** branch of the decision If/Else (Advance and NeedsReview applications), add a second **Invoke agent** node.
2. Click **Create new agent** and name it `Response-Agent`.
3. Write the system instructions:
   > "You are a recruiting coordinator. Given a screened job application, draft a short, professional candidate email. For **Advance** decisions, invite the candidate to schedule a first interview and mention one specific strength from their application. For **NeedsReview** decisions, request the 1–2 specific missing details a recruiter needs to make a decision. Keep it under 6 sentences. Tone: warm, professional, inclusive. No emojis."
4. Set **Input** to `Local.ScreeningOutputText`.
5. Store the output in a variable named `ResponseOutputText`.
6. Save. Connect through to the **End** node.

> **Talking point:** "We now have two specialized agents — one that screens, one that writes the candidate email. Each agent has a single, clear responsibility. This is the separation-of-concerns principle applied to AI orchestration: keep each agent focused, and let the workflow handle routing."

---

### Step 8 — Test in the visual designer

1. Click **Preview** (chat panel on the right).
2. Type: `Start processing job applications`
3. Watch the execution trace in the canvas — highlight which path each application takes.
4. Point out:
   - The For-Each iterating three times
   - The strong Senior Backend Engineer routing to **Advance** and receiving a drafted interview-invite email
   - The clearly under-qualified application routing to **Reject** with a standard notice
   - The vague Cloud Architect (or any low-confidence application) hitting the human-review path

> **Talking point:** "The visual trace is one of the key advantages of Foundry workflows over code-only orchestration. You can see exactly which branch was taken and inspect the intermediate variable values — `ScreeningOutputJson` — at each step."

---

### Step 9 — Show the YAML and version history (brief)

1. Click the **YAML** view toggle to show the raw workflow definition.
2. Point out that this can be exported, committed to source control, and re-imported.
3. Click **Version history** and note that every save creates an immutable version that can be rolled back.

> **Talking point:** "The YAML is the source of truth. Once you're happy with a workflow, you commit this file to your repo and deploy it like any other artifact. Version history gives you a safety net while you iterate."

---

### Step 10 — Invoke the workflow from Python code

A complete, runnable invoker lives in [`workflow-demo-py/`](workflow-demo-py/) — no need to clone the lab. It connects with `AIProjectClient`, references the published workflow by name, creates a conversation, streams the run, and prints a tidy card per application.

**One-time setup** — from the [`workflow-demo-py/`](workflow-demo-py/) folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit WORKFLOW_NAME to match what you published
az login
```

`.env` already points `PROJECT_ENDPOINT` at the demo project above. Set `WORKFLOW_NAME` to the exact name of the workflow you published in Step 1 (`Contoso-Job-Application-Triage`).

Run it:

```powershell
python invoke_workflow.py
```

The core of [`invoke_workflow.py`](workflow-demo-py/invoke_workflow.py) is the reference-by-name + streamed run:

```python
workflow = {"name": os.getenv("WORKFLOW_NAME", "Contoso-Job-Application-Triage")}

conversation = openai_client.conversations.create()

stream = openai_client.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": workflow["name"], "type": "agent_reference"}},
    input="Start processing job applications",
    stream=True,
)

for event in stream:
    if event.type == "response.completed":
        response = openai_client.responses.retrieve(event.response.id)
        print_workflow_output(response.output_text)
```

> **Talking point:** "The workflow is just another named asset in your Foundry project. From code you reference it by name through the same `AIProjectClient` you already know. The streaming event loop lets you display results in real time as each application is processed — exactly what a production front-end or applicant-tracking integration would do."

---

### Summary

| What was demonstrated | Key concept |
|---|---|
| Blank workflow created in Foundry portal | Visual canvas, node types |
| Set Variable + For-Each loop | Iterating a list without duplicate nodes |
| Screening Agent with JSON schema output | Structured outputs enable reliable control flow |
| If/Else on `confidence > 0.6` | Human-in-the-loop / manual-review pattern |
| If/Else on `decision = "Reject"` | Decision-based routing |
| Response Agent for Advance/NeedsReview | Multi-agent separation of concerns |
| Preview with execution trace | Live debugging in the canvas |
| YAML view + version history | Maintainability and source control |
| Python SDK invocation ([`workflow-demo-py/`](workflow-demo-py/)) | Embedding workflows in applications |

Students now complete the exercise lab independently — that lab uses a different scenario (a ContosoPay customer-support triage workflow), so this demo and the lab reinforce the same workflow mechanics across two domains:
https://learn.microsoft.com/en-us/training/modules/build-agent-workflows-microsoft-foundry/9-exercise

---

### Provisioning the workflow without the portal

The workflow can be created two ways:

1. **Portal visual designer** — follow Steps 1–9 above.
2. **Code** — run [`create_workflow.py`](workflow-demo-py/create_workflow.py) from the `workflow-demo-py/` folder. It publishes the two prompt agents (`Screening-Agent` with the strict JSON schema, `Response-Agent`) and the `Contoso-Job-Application-Triage` workflow, then `invoke_workflow.py` runs it.

```powershell
python create_workflow.py   # publishes agents + workflow
python invoke_workflow.py   # runs it
```

### Demo resources

| Resource | Name / value |
|---|---|
| Foundry project | `ai-103-demos` (`ai-103-demos-resource`) |
| Model deployment | `gpt-5.4` (GlobalStandard) |
| Screening agent | `Screening-Agent` (prompt agent, strict JSON schema) |
| Response agent | `Response-Agent` (prompt agent) |
| Workflow | `Contoso-Job-Application-Triage` |

Permissions: **Azure AI User** (or higher) on the project for the signed-in identity; **Contributor** on the project to create/edit workflows in the portal.

### CSDL dialect gotcha

The Foundry **portal** workflow CSDL differs from the Agent Framework declarative-workflow docs:

| Logic | Agent Framework docs | Foundry portal CSDL (use this) |
|---|---|---|
| If/Else | `kind: If` + `then:` / `else:` | `kind: ConditionGroup` + `conditions:` / `elseActions:` |
| For-Each | `kind: Foreach` + `source:` / `itemName:` | `kind: Foreach` + `items:` / `value:` / `index:` |

Publishing a `kind: If` workflow via the SDK is accepted and even runs the non-conditional prefix, but the conditional subtree is silently dropped — the portal renders an empty canvas and routing never executes. Build in the portal and export the YAML as the source of truth, as captured in [`Contoso-Job-Application-Triage.yaml`](Contoso-Job-Application-Triage.yaml).
