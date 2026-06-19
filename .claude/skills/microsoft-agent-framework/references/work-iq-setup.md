# Work IQ Setup Reference

Work IQ (`@microsoft/workiq`) is a CLI + MCP server that gives an agent read access to a user's live M365 data — mail, calendar, SharePoint, Teams — under that user's own Copilot permissions. It uses **delegated (On-Behalf-Of) auth only**; there is no app-only path.

Two runtime modes:

| Mode | Command | Use case |
|---|---|---|
| CLI | `workiq ask -q "..."` | Interactive queries, provisioning, diagnostics |
| MCP server | `npx -y @microsoft/workiq mcp` | Register in VS Code / Copilot / agent MCP host |

Both modes share the same auth, billing, and provisioning prerequisites.

## Install

```bash
npm install -g @microsoft/workiq
```

Or use `npx` directly without installing:

```bash
npx -y @microsoft/workiq mcp
```

## Provisioning Chain

Each step must complete in order. Later steps fail with confusing errors if an earlier one is missing — step 1 is the root cause of almost every first-time failure.

### Who needs which role

| Step | Required role |
|---|---|
| 1. Provision the service principal | Global Administrator |
| 2. Accept EULA | Any user |
| 3. Grant consent | Any user (after SP exists) |
| 4. Activate billing | Global Admin or Billing Admin |
| 5. Query | Any user in the billing policy scope |

### Step 1 — Provision the Work IQ service principal (one-time, Global Admin)

The missing SP is the root cause of `Your tenant does not yet have the WorkIQ service configured` and the WAM `IncorrectConfiguration` error (3399614468) on `workiq auth consent`. This must be done before any other step.

**Option A — Azure CLI:**

```azurecli
az ad sp create --id fdcc1f02-fc51-4226-8753-f668596af7f7
```

**Option B — Graph Explorer** (browser, Global Admin account):

```json
POST https://graph.microsoft.com/v1.0/servicePrincipals
{
  "appId": "fdcc1f02-fc51-4226-8753-f668596af7f7"
}
```

`201 Created` = success. A conflict response means the SP already exists — continue.

SP details for reference:
- App ID: `fdcc1f02-fc51-4226-8753-f668596af7f7`
- Scope: `WorkIQAgent.Ask` (ID `0b1715fd-f4bf-4c63-b16d-5be31f9847c2`)
- Audience: `api://workiq.svc.cloud.microsoft`

### Step 2 — Accept the EULA

```bash
workiq accept-eula
```

### Step 3 — Grant consent (interactive)

```bash
workiq auth consent
```

Interactive browser sign-in. Only works after Step 1. The CLI auths against the signed-in account's home tenant; manage account with `workiq config` / `workiq auth login`.

### Step 4 — Activate usage-based billing (portal only)

This step cannot be scripted. A plain `403 Forbidden` on `workiq ask` with no scope error means this gate is missing.

Work IQ API reached GA on 2026-06-16 with consumption pricing via Copilot Credits. No queries are possible until a billing policy is active.

1. Go to the [Microsoft 365 admin center](https://admin.microsoft.com).
2. Navigate to **Copilot** > **Cost Management** > **Get Started**.
3. Activate a spending policy: select an Azure subscription, set monthly limits and alerts, save.
4. Ensure the querying user is in scope of the policy.
5. Wait 15–30 minutes — the index takes time to build after billing is activated.

### Step 5 — Run a query

```bash
workiq ask -q "summarize my recent emails"
```

Add `-v` for request-ID and conversation-ID diagnostics.

## CLI Build Note

Build 1.0.0.28144 has **no `-t` / `--tenant-id` flag on `ask`** — the Microsoft Learn docs list one, but this build does not expose it. Auth is determined by the signed-in account's home tenant. Use `workiq config` and `workiq auth login` to switch accounts. Other available subcommands: `auth (login|logout|consent)`, `config (set|unset|show|reset)`, `mcp`, `agents`, plus entity operations (`fetch`, `create`, `search-paths`, etc.).

## Error Decoding

| Symptom | Cause | Fix |
|---|---|---|
| `Your tenant does not yet have the WorkIQ service configured` | Work IQ SP not provisioned | Complete Step 1, retry Step 3 |
| WAM `IncorrectConfiguration` (error 3399614468) | SP not provisioned | Complete Step 1 |
| WAM `IncorrectConfiguration` (error 3399614466) | Custom app registration missing broker redirect URI `ms-appx-web://microsoft.aad.brokerplugin/<client_id>` | Add the broker redirect URI to the app registration |
| `403 Forbidden` (no scope error in response) | User not covered by a usage-based billing plan, or missing M365 Copilot license | Complete Step 4, wait 15–30 min, retry |
| `403 Forbidden` with `Required scopes = [...]` | Admin consent for `WorkIQAgent.Ask` not granted | Rerun `workiq auth consent` (Step 3) |
| `401 Unauthorized` | Token audience mismatch — token must target `api://workiq.svc.cloud.microsoft` | Check the token audience claim |
| Empty 200 / no agent text | Index still building after billing or license change | Wait 15–30 minutes and retry |

## MCP Server Registration

Register Work IQ as an MCP server in any host that supports it (VS Code, Copilot, Agent Framework agent):

```json
{
  "mcpServers": {
    "workiq": {
      "command": "npx",
      "args": ["-y", "@microsoft/workiq", "mcp"]
    }
  }
}
```

The same provisioning prerequisites (Steps 1–4) apply. The MCP server auths against the signed-in account, identical to the CLI.

## Worked Example

See [`../../../../modules/02-agents/05-m365/setup-workiq.md`](../../../../modules/02-agents/05-m365/setup-workiq.md) for a complete end-to-end setup walkthrough tied to the 05-m365 Store Ops demo, including the `provision-workiq.azcli` script and verification steps.

**Running the 05-m365 demo scripts headlessly:**

`provision-agent.py` — run once (or re-run safely). It resolves the vector store by name (`store-ops-index`) and reuses it if found; it creates a new agent version each run (v1, v2, v3 ... — this is expected, not duplicate resources).

```bash
.venv/Scripts/python.exe provision-agent.py
```

`workiq_demo.py` — interactive menu; pipe stdin to run non-interactively (option 1 = Store-Ops Email Digest, blank = accept default, 0 = exit):

```bash
echo -e "1\n\n0" | .venv/Scripts/python.exe workiq_demo.py
```

Expected output includes `[MCP Proxy] Registered N remote tools from https://workiq.svc.cloud.microsoft/mcp` and a combined tool count (file-search + Work IQ). If the agent reports no emails found, the tools still worked — see [Healthy Run Signature](work-iq-troubleshooting.md#healthy-run-signature).

## References

- [Enable your tenant for Work IQ](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/enable-work-iq)
- [Microsoft Work IQ CLI](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/cli)
- [Understand usage-based billing and Copilot Credits](https://learn.microsoft.com/microsoft-365/copilot/usage-based-billing-overview-copilot-credits)
