# Agent 365 CLI Reference

The Agent 365 CLI (binary `a365`, NuGet `Microsoft.Agents.A365.DevTools.Cli`) is the **governance / publishing plane** for Microsoft 365. It is framework-agnostic and works with agents built on any platform (Foundry, Agent Framework, Copilot Studio, …).

> **It does NOT deploy *into* Foundry.** Foundry (or any host) runs the agent; `a365` registers its **Entra agent identity**, grants **Work IQ / MCP** permissions, packages `manifest.zip`, and publishes it to the **Microsoft 365 admin center**. It is the programmatic alternative to the Foundry portal publishing wizard.

## Install & Update

```powershell
# Install (global .NET tool — requires .NET 8.0+)
dotnet tool install --global Microsoft.Agents.A365.DevTools.Cli

# Update
dotnet tool update --global Microsoft.Agents.A365.DevTools.Cli

# Verify
a365 -h
```

Tool location: `%USERPROFILE%\.dotnet\tools` (Windows), `$HOME/.dotnet/tools` (Linux/macOS). Cross-platform — install .NET 8.0+ first per OS.

> Microsoft's recommended path is the **AI-guided setup** (an AI coding agent following `aka.ms/agent365enable`) which installs the CLI and runs the commands for you. The manual commands below are for CI/CD and troubleshooting.

## Command Surface

There is **no `init` and no `deploy` top-level verb** — initialization is `config init` (or config-free `--agent-name`), and code deployment is delegated to `az` / GitHub Actions. The Agent-365 verbs are `setup`, `develop`, `develop-mcp`, `publish`, `query-entra`, `cleanup`, `logs`.

| Command | Purpose |
| --- | --- |
| `a365 config init -c ./a365.config.json` | Initialize / apply config after editing it |
| `a365 setup requirements` | Validate / repair prerequisites; auto-create the `Agent 365 CLI` client app |
| `a365 setup all` | Run all setup steps: requirements → blueprint → permissions → identity → registration → config sync. Supports config-free `--agent-name`. |
| `a365 setup blueprint` | Create the agent blueprint (Entra app registration); register/update the messaging endpoint |
| `a365 setup blueprint --endpoint-only --messaging-endpoint https://.../api/messages` | Register the endpoint after the agent code is deployed |
| `a365 setup permissions [mcp\|bot\|copilotstudio\|custom]` | Configure OAuth2 grants / inheritable permissions |
| `a365 develop add-mcp-servers` / `remove-mcp-servers` | Manage MCP tool servers in `ToolingManifest.json` |
| `a365 develop list-available` / `list-configured` | List catalog / configured MCP servers |
| `a365 develop get-token` | Get bearer tokens to test MCP servers |
| `a365 develop-mcp publish` / `evaluate` / `list-environments` | Manage / evaluate MCP servers in Dataverse environments |
| `a365 publish` | Update IDs in `manifest.json`, build `manifest.zip`, print admin-center upload steps |
| `a365 query-entra [blueprint-scopes\|inheritance\|instance-scopes]` | Inspect declared permissions, inheritance, instance consent |
| `a365 cleanup [azure\|blueprint\|instance]` | Tear down resources |
| `a365 logs export` | Export a redacted diagnostic log for Microsoft support |

## End-to-End Workflow (agent → M365 / Teams)

1. **Config** — `a365 config init` produces `a365.config.json` (tenant, subscription, project path, messaging endpoint).
2. **Setup** — `a365 setup all` registers the Entra agent identity (blueprint), provisions Azure resources, configures Graph + Bot API + inheritable permissions, and writes generated IDs to `a365.generated.config.json`.
3. **Deploy the code** — deploy the agent *code* with standard tooling (`az webapp deploy` / GitHub Actions), then register the now-known endpoint with `setup blueprint --endpoint-only`.
4. **Publish** — `a365 publish` packages `manifest.json` + icons into `manifest.zip` and prints upload steps for the M365 admin center (`https://admin.cloud.microsoft/#/agents/all`).
5. **Add & test** — in Teams → Apps, add the agent (may need admin approval) and chat to verify.

## Config Files

- **`a365.config.json`** — developer-authored: tenant, subscription, `messagingEndpoint`, `deploymentProjectPath`, optional `authMode`, `customBlueprintPermissions`.
- **`a365.generated.config.json`** — produced by `setup`: generated agent/blueprint IDs, endpoints, per-resource admin-consent URLs.
- **`manifest.json` → `manifest.zip`** — built by `a365 publish` for admin-center upload.
- **`ToolingManifest.json`** — configured MCP servers.
- Config sync also writes `Connections.ServiceConnection`, `Agent365Observability`, `TokenValidation` into the project's `appsettings.json` / `.env`.

## Auth & Consent

- Uses Azure CLI auth (`az login`); tenant auto-detected from `az account show` (override `--tenant-id`).
- Requires a custom Entra app registration named **`Agent 365 CLI`** (`setup requirements` can auto-create it).
- Roles (least → most): **Agent ID Developer** (blueprint + inheritable perms, no admin consent) → **Agent ID Administrator** → **Global Administrator** (completes admin consent in one run). `setup` baseline: Azure **Contributor** + **Agent ID Developer**. Admin-center upload (publish) requires **Global Administrator**.
- `--authmode`: `obo` (default, no admin role) / `s2s` (app-role assignments, needs App Admin or GA) / `both`.
- When a non-GA runs `setup all`, the CLI completes what it can and saves admin-consent URLs to `a365.generated.config.json` for a Global Admin to grant later.

## Status

**Preview.** The command surface is actively churning (the AI-teammate type is gated behind the Frontier preview program; some `develop-mcp` verbs were removed and a V1→V2 MCP permission migration is in progress). Confirm the current surface with `a365 -h` and the docs before scripting.
