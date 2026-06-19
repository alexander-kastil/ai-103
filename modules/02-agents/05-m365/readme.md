# Integrate your agent with Microsoft 365
https://learn.microsoft.com/en-us/training/modules/integrate-foundry-agent-with-m365/

---

## Instructor Demo Guide

This demo shows how to publish a Microsoft Foundry agent to Microsoft Teams and Microsoft 365 Copilot using the Foundry portal publishing wizard, then introduces Work IQ for accessing Microsoft 365 data from agents.

The running example is a **Contoso Retail store-operations help desk**, an agent that store managers chat with in Teams to get fast answers on POS troubleshooting, returns and refunds, opening and closing the store, and inventory restock.

Self-contained demo assets live next to this guide:

- [`store-ops-agent-py/`](store-ops-agent-py/): provision script, four store-operations grounding documents, and a sample [`agent.yaml`](store-ops-agent-py/assets/agent.yaml)
- [`store-ops-workiq-py/`](store-ops-workiq-py/): a runnable Work IQ script that extends `store-ops-assistant` with live M365 data

**Estimated time:** 25-35 minutes

---

### Demo resources

These resources were provisioned by `store-ops-agent-py/provision-agent.py` and are ready in the Foundry project.

| Resource | Value |
|---|---|
| Agent name | `store-ops-assistant` |
| Vector store name | `store-ops-index` |
| Vector store ID | `vs_Wjv76peAvlRaSn6Oq4dAcovT` |
| Project endpoint | `https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos` |
| Model deployment | `gpt-5.4` |

---

### Prerequisites

- An existing agent built and tested in the Microsoft Foundry portal (ai.azure.com). Build it quickly from the assets below (Part 0).
- **Azure AI Project Manager** role on the Foundry project
- Permissions to create resources in the Azure subscription (Azure Bot Service will be provisioned)
- Permissions to register applications in Microsoft Entra ID
- **Microsoft.BotService** resource provider registered in the subscription
- A Microsoft 365 tenant with Teams enabled and custom apps allowed
- Two PNG icons prepared: 32x32 px (small) and 192x192 px (large)
- A privacy policy URL and terms of use URL (can be placeholder URLs for demo purposes)
- For Part 4 (Work IQ): Python 3.13+, an M365 Copilot license, and Node.js (Work IQ runs via `npx`)
- Work IQ requires tenant provisioning before first use. See [setup-workiq.md](setup-workiq.md) (provision the service principal, grant consent, activate usage-based billing)

Grounding documents from [`store-ops-agent-py/assets/`](store-ops-agent-py/assets/), to upload when you build the demo agent:

- [`pos-troubleshooting.md`](store-ops-agent-py/assets/pos-troubleshooting.md): diagnosing register, card-reader, printer, network, and pricing issues
- [`returns-and-refunds-policy.md`](store-ops-agent-py/assets/returns-and-refunds-policy.md): return windows, refund methods, final-sale items, approval thresholds
- [`store-opening-closing-checklist.md`](store-ops-agent-py/assets/store-opening-closing-checklist.md): the opening and closing procedures and end-of-day reporting
- [`inventory-restock-procedure.md`](store-ops-agent-py/assets/inventory-restock-procedure.md): receiving, replenishment, cycle counts, damaged/recalled stock

---

#### Part 0 - Build the demo agent (optional, 5 min)

If you don't already have an agent in the portal, build the store-ops assistant quickly so you have something to publish:

1. In [https://ai.azure.com](https://ai.azure.com), go to **Build > Agents** and create an agent named `store-ops-assistant`.
2. Paste the instructions from [`store-ops-agent-py/assets/agent.yaml`](store-ops-agent-py/assets/agent.yaml) into the **Instructions** field.
3. In **Tools**, choose **Upload files**, create a new vector index named `store-ops-index`, and upload all four documents from [`store-ops-agent-py/assets/`](store-ops-agent-py/assets/).
4. Test in the chat panel: `A register won't connect to the store server, what do I do?` and confirm it cites `pos-troubleshooting.md`.

> **Talking point:** "This is a different agent from the one students build in the lab. Their lab agent is an HR/company-policy assistant. Ours is a store-operations help desk, same publishing mechanics, different domain, so you'll see the workflow twice from two angles."

##### Optional: provision with a script instead

If you prefer a reproducible, repeatable setup over clicking through the portal, `store-ops-agent-py/provision-agent.py` does the same work from the command line. It creates (or reuses) the `store-ops-index` vector store, uploads the four grounding documents, and registers a versioned `store-ops-assistant` agent in your Foundry project.

```powershell
cd store-ops-agent-py
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # fill in PROJECT_ENDPOINT; MODEL_DEPLOYMENT_NAME defaults to gpt-5.4
az login
python provision-agent.py
```

The script prints the agent ID and vector store ID when it finishes. The agent is then ready in the portal for the publishing steps that follow.

---

#### Part 1 - Understand the publishing architecture (5 min)

1. Open a browser to [https://ai.azure.com](https://ai.azure.com) and navigate to your Foundry project.

2. Point out the `store-ops-assistant` agent in the agent list.

   > **Talking point:** "The agent works perfectly here in the Foundry playground. But store managers spend their day in Teams, not in this portal. Publishing bridges that gap by creating a managed Azure resource with a stable endpoint and a dedicated identity that Microsoft 365 can reach."

3. Briefly draw or point to the publishing architecture:
   - Foundry agent → Azure Bot Service → Microsoft Teams / M365 Copilot
   - Publishing also registers a Microsoft Entra ID application for authentication.

   > **Talking point:** "Notice that publishing creates a *new* agent identity, separate from your project identity. This matters for permissions: any Azure resources your tools access (the vector index behind our store-ops docs, for example) need to grant rights to this new identity, not to your personal account."

4. Show the two distribution scopes side by side:

   | Scope | Where it appears in Teams | Admin approval needed? |
   |---|---|---|
   | Shared | "Your agents" | No, available immediately |
   | Organization | "Built by your org" | Yes, M365 admin must approve |

   > **Talking point:** "For this demo we'll use Shared scope, which is perfect for testing and a small pilot, say the managers of three stores. When you're ready to roll out to every store in the region, you switch to Organization scope and route it through the admin center."

---

#### Part 2 - Run the Foundry portal publishing wizard (10 min)

1. In the Foundry portal, select the `store-ops-assistant` agent and click **Publish**.

2. In the publishing dialog, click **Publish** again, then choose **Publish to Teams and Microsoft 365 Copilot**.

   > **Talking point:** "The wizard handles provisioning the Azure Bot Service resource automatically. You don't need to create it manually in the Azure portal."

3. In the **Azure Bot Service** dropdown, select **Create an Azure Bot Service**. Wait for provisioning to complete (typically under a minute).

4. Fill in the metadata fields:

   - **Name**: `Store Ops Assistant` (the display name managers see in the Teams agent store)
   - **Description**: "Answers Contoso Retail store-operations questions: POS, returns, opening/closing, inventory"
   - **Icons**: upload the 32x32 and 192x192 PNG files
   - **Publisher information**: organization name and contact email
   - **Privacy policy / Terms of use**: paste the placeholder URLs

   > **Talking point:** "These metadata fields appear in the Teams store listing. Never put API keys or secrets here. They are visible to anyone who finds the agent."

5. Under **Publish scope**, select **Shared**.

6. Click **Prepare Agent** and wait 1-2 minutes for packaging to complete.

7. When ready, click **Download the package** to save the `.zip` file locally.

   > **Talking point:** "Downloading the package lets us sideload it into Teams for testing before we commit to organization-wide distribution. The package is a standard Teams app manifest."

---

#### Part 3 - Sideload and test in Microsoft Teams (8 min)

1. Open Microsoft Teams (desktop or web).

2. Go to **Apps** > **Manage your apps** > **Upload an app** > **Upload a custom app**.

3. Select the downloaded `.zip` file. Teams installs the app and adds it to your apps list.

4. Open the agent and send a test message, for example: `What can you help me with?`

   > **Talking point:** "We're now talking to our Foundry store-ops agent directly inside Teams chat. The message travels from Teams, through Azure Bot Service, to the Foundry Agent Service, and back. The store manager never needs to open ai.azure.com."

5. Send a second message that exercises the grounding documents, for example:

   ```
   A card reader is declining every card on one lane but the others are fine. What should I do?
   ```

   The agent should walk through the card-reader steps from [`store-ops-agent-py/assets/pos-troubleshooting.md`](store-ops-agent-py/assets/pos-troubleshooting.md) and cite the source.

6. Walk through the quick post-publish checklist:
   - Agent responds in Teams
   - Response content matches what the playground produced
   - Response time is acceptable
   - Knowledge citations (the store-ops docs) appear

   > **Talking point:** "If knowledge grounding works in the Foundry playground but the agent gives generic answers here, the first thing to check is RBAC permissions on the published agent identity. The new identity doesn't automatically inherit your development-time access to the vector index."

---

#### Part 4 - Work IQ: accessing live M365 store-ops data (5 min)

Where file-search grounding answers from *documents*, Work IQ answers from a manager's *live Microsoft 365 data*: store-ops emails, the district sync meeting, Teams threads. The [`store-ops-workiq-py/`](store-ops-workiq-py/) script extends `store-ops-assistant` with Work IQ tools: it creates a new version of the same base agent that combines file-search grounding with live M365 data access, then runs the Responses-API tool-call loop against that version.

1. Explain Work IQ first.

   > **Talking point:** "Work IQ is a CLI and MCP server that gives your agents access to a user's emails, calendar meetings, SharePoint documents, and Teams channel messages, all through Microsoft 365 Copilot permissions. The user only ever sees data they already have access to. For our store manager, that means questions like 'summarize this week's store-ops emails' or 'prep me for the district sync'."

2. Show the two modes side by side:

   | Mode | How to invoke | Best for |
   |---|---|---|
   | CLI | `workiq ask -q "summarize this week's store-ops emails"` | Quick queries, scripts |
   | MCP server | Configured in an agent / VS Code / Copilot | Integrated AI assistant experience |

3. Show the install commands (no need to run them live):

   ```
   npm install -g @microsoft/workiq
   workiq accept-eula
   ```

   > **Talking point:** "Work IQ requires admin consent in the Entra tenant because it queries org-wide data through Microsoft Graph. Check with IT before enabling it. The product is still in preview."

4. Explain the demo architecture before running it.

   > **Talking point:** "The script resolves the store-ops-index vector store by name, fetches the Work IQ MCP tool list at runtime, and creates a new version of store-ops-assistant whose tools combine file-search with all the Work IQ tools. The model then decides which tool to call, the same Responses-API loop you've already seen."

5. If time permits, run the demo script. From [`store-ops-workiq-py/`](store-ops-workiq-py/):

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   copy .env.example .env   # endpoint is pre-filled; MODEL_DEPLOYMENT_NAME defaults to gpt-5.4
   az login
   python workiq_demo.py
   ```

   Pick option **1** (Store-Ops Email Digest). The agent calls Work IQ MCP tools to read the manager's mailbox and returns a themed digest with sources.

   > **Talking point:** "Same Responses-API + tool-call loop you saw with custom tools. The tools come from the Work IQ MCP server instead of local Python functions. The agent discovers them at runtime and the model decides when to call them. File-search and Work IQ tools coexist in the same agent version."

---

#### Part 5 - Wrap-up: the update cycle (2 min)

> **Talking point:** "Publishing is not a one-time action. When you improve the store-ops agent's instructions, add a new policy document, or fix issues, you repeat the wizard, generate a new package, and re-upload. For Organization scope deployments, check your tenant's app policies, some updates require re-approval. Build testing into every release."

---

### Summary

| Topic | Key takeaway |
|---|---|
| Agent Application | Publishing creates a managed resource with a stable endpoint and its own Entra identity |
| Publishing wizard | Foundry portal provisions Azure Bot Service and generates a Teams app package in a few clicks |
| Distribution scopes | Shared = immediate, personal/pilot; Organization = tenant-wide, requires admin approval |
| Post-publish permissions | Grant RBAC roles to the published agent identity for any Azure resources its tools access (e.g. the store-ops vector index) |
| Sideload testing | Upload the `.zip` to Teams > Manage your apps > Upload a custom app before broad rollout |
| Knowledge grounding | The store-ops docs in [`store-ops-agent-py/assets/`](store-ops-agent-py/assets/) ground answers and produce citations in Teams |
| Work IQ | MCP server that connects agents to live M365 data (store-ops emails, meetings, Teams); requires M365 Copilot license and admin consent |
| Iteration | Changes require re-publishing; organization scope may require re-approval |

---

**Students do the labs themselves**: an HR / company-handbook knowledge agent published to Teams and Copilot, plus the optional Work IQ workplace-intelligence lab:
https://learn.microsoft.com/en-us/training/modules/integrate-foundry-agent-with-m365/7-exercise
