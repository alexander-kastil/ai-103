# Work IQ Troubleshooting Reference

Symptom-first diagnostic guide for Work IQ (`@microsoft/workiq`). For ordered provisioning steps, see [work-iq-setup.md](work-iq-setup.md).

## Layer Framing

Work IQ failures fall into five layers, in this order of diagnosis:

1. **Install/process** — npm binary lock, stale process, version mismatch
2. **Auth/broker** — WAM not available, broker package corrupted, account not signed in
3. **Consent** — service principal missing, admin consent not granted
4. **Billing** — no usage-based billing policy, no M365 Copilot license in scope
5. **Query** — index not built yet, audience mismatch in token

Always confirm the layer before diving deep. Run state checks first.

---

## Quick State Checks

Before any other step, confirm what is actually installed and signed in:

```bash
workiq version
workiq config show
```

```azurecli
az account show --query "{tenantId:tenantId, user:user.name}" -o json
az ad sp show --id fdcc1f02-fc51-4226-8753-f668596af7f7 --query "{displayName:displayName, appId:appId}" -o json
```

`az ad sp show` returning "does not exist" is the root cause of most first-run failures — it means the Work IQ service principal has never been provisioned in your tenant. Go to [work-iq-setup.md Step 1](work-iq-setup.md) before anything else.

---

## Triage Table

| Symptom | Layer | Likely cause | Where to fix |
|---|---|---|---|
| `npm error code EBUSY ... workiq.exe ... resource busy or locked` | Install/process | Running `workiq` process holds a file lock on the binary | [EBUSY on install/uninstall](#ebusy-on-installuninstall-windows) |
| `workiq auth consent` hangs or crashes without a browser prompt | Auth/broker | WAM account picker component not registered | [WAM broker recovery](#wam-broker-recovery-windows) |
| WAM `IncorrectConfiguration` (error 3399614468) | Consent | SP not provisioned | [work-iq-setup.md Step 1](work-iq-setup.md) |
| `Your tenant does not yet have the WorkIQ service configured` | Consent | SP not provisioned | [work-iq-setup.md Step 1](work-iq-setup.md) |
| WAM `IncorrectConfiguration` (error 3399614466) | Auth/broker | Custom app registration missing broker redirect URI | Add `ms-appx-web://microsoft.aad.brokerplugin/<client_id>` to the app registration |
| Falls back to "Graph proxy" with a warning | Consent | SP not provisioned; degraded mode only | [work-iq-setup.md Step 1](work-iq-setup.md) |
| `403 Forbidden` (no scope error in response body) | Billing | No usage-based billing policy, or missing M365 Copilot license | [work-iq-setup.md Step 4](work-iq-setup.md), wait 15–30 min |
| `403 Forbidden` with `Required scopes = [...]` | Consent | Admin consent for `WorkIQAgent.Ask` not granted | Run `workiq auth consent` ([work-iq-setup.md Step 3](work-iq-setup.md)) |
| `401 Unauthorized` | Query | Token audience mismatch | Token must target `api://workiq.svc.cloud.microsoft` — check the `aud` claim |
| Empty 200 / no agent text | Query | Index still building after billing or license change | Wait 15–30 minutes and retry |
| Work IQ tool calls succeed (MCP connected, `ask` returns) but agent reports no emails / no data found | Query/Data | Signed-in account's mailbox has no matching M365 content for the query, OR the wrong account is signed in — this is NOT an error | Run `workiq config show` to confirm the signed-in account; query a window or account that has data, or seed test data |

---

## Operational Issues

### EBUSY on install/uninstall (Windows)

**Symptom:** npm fails with something like:

```
npm error code EBUSY
npm error syscall copyfile
npm error path ...\workiq.exe
npm error dest ...\workiq.exe
npm error errno -4082
npm error EBUSY: resource busy or locked
```

**Cause:** A `workiq` process (often a leftover MCP server spawned by VS Code, Copilot, or Claude Code) holds an OS-level file lock on `workiq.exe`. `npm install --force` does not help — `--force` disables npm safety checks, not Windows file locks.

**Fix — uninstall:**

```powershell
Get-Process workiq -ErrorAction SilentlyContinue | Select-Object Id, Path
Get-Process workiq -ErrorAction SilentlyContinue | Stop-Process -Force
npm uninstall -g @microsoft/workiq
```

**Fix — reinstall:** Stop any running workiq first to avoid re-locking the binary immediately:

```powershell
Get-Process workiq -ErrorAction SilentlyContinue | Stop-Process -Force
npm install -g @microsoft/workiq
```

Stopping the process drops any active Work IQ MCP connection in the host (VS Code, Copilot, Claude Code) — this is expected. After reinstalling, the host will reconnect on the next request.

**Avoid re-locking:** Check that your MCP host config is not set to auto-respawn `workiq mcp` — if it is, the binary will be re-locked the moment npm finishes, and the next update will hit EBUSY again.

---

### WAM broker recovery (Windows)

**When to use this:** `workiq auth consent` throws WAM errors and the SP is already confirmed provisioned (i.e., `az ad sp show` succeeds). If the SP is missing, go to [work-iq-setup.md Step 1](work-iq-setup.md) first — that is the far more common cause of WAM `IncorrectConfiguration`.

WAM (Web Account Manager) is the Windows authentication broker that Work IQ uses for delegated sign-in. Its underlying packages can become unregistered after a Windows update.

**Step 1 — Re-register the Entra WAM broker plugin** (PowerShell as Administrator):

```powershell
if (-not (Get-AppxPackage Microsoft.AAD.BrokerPlugin)) {
    Add-AppxPackage -Register "$env:windir\SystemApps\Microsoft.AAD.BrokerPlugin_cw5n1h2txyewy\Appxmanifest.xml" -DisableDevelopmentMode -ForceApplicationShutdown
}
Get-AppxPackage Microsoft.AAD.BrokerPlugin
```

**Step 2 — Re-register the account picker** (PowerShell as Administrator), if the account picker dialog does not appear:

```powershell
if (-not (Get-AppxPackage Microsoft.AccountsControl)) {
    Add-AppxPackage -Register "$env:windir\SystemApps\Microsoft.AccountsControl_cw5n1h2txyewy\AppxManifest.xml" -DisableDevelopmentMode -ForceApplicationShutdown
}
Get-AppxPackage Microsoft.AccountsControl
```

**Step 3 — Clear cached auth and retry:**

```bash
workiq auth logout
workiq auth login
workiq auth consent
```

**Prerequisites WAM enforces:** Windows 10+ (build 1903 or later) or Windows Server 2019+, active internet connection, the account must exist in Microsoft Entra ID.

---

## Healthy Run Signature

A successful agent run with Work IQ does NOT always produce populated results — data absence is not a failure. Confirm success by the log lines, not by the agent's answer content.

A healthy run produces all of the following:

1. `[MCP Proxy] Registered N remote tools from https://workiq.svc.cloud.microsoft/mcp` — MCP connected and auth succeeded silently (no consent prompt, no 403).
2. Combined file-search + Work IQ tool list registered (typically 11 tools total: file-search tools + the Work IQ `ask` tool and peers).
3. A new agent version created (version number increments each run — this is expected, not duplicate resources).
4. The Responses-API tool loop completes; the agent's `ask(...)` calls return without error.

If all four are present and the agent says "no emails found" or "no matching data", the **tools worked** — the account simply has no M365 content matching the query. This is a data/account issue, not a system failure.

---

## Verbose Diagnostics

Add `-v` to any `workiq ask` call to capture the `request-id` and `conversation-id` — include both when filing issues:

```bash
workiq ask -q "summarize my recent emails" -v
```

Issues and known bugs: [github.com/microsoft/work-iq-mcp](https://github.com/microsoft/work-iq-mcp)

---

## References

- [Enable your tenant for Work IQ](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/enable-work-iq)
- [Using MSAL.NET with WAM — Troubleshooting](https://learn.microsoft.com/entra/msal/dotnet/acquiring-tokens/desktop-mobile/wam#troubleshooting)
- [WAM error codes](https://learn.microsoft.com/entra/msal/dotnet/advanced/exceptions/wam-errors)
- [Fix authentication issues in Microsoft 365 apps](https://learn.microsoft.com/troubleshoot/microsoft-365/admin/authentication/automatic-authentication-fails)
