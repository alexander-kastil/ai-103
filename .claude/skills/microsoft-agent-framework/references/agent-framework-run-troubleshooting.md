# Agent Framework Local Run Troubleshooting Reference

Symptom-first diagnostic guide for **running** Agent Framework / Foundry demos locally — single-script demos and multi-server A2A systems (`run_all.py` launching uvicorn servers plus a console client). Windows-first, since that is the class delivery platform. For deployment (not local run), see [agent-framework-deploy.md](agent-framework-deploy.md). For the run workflow itself, see the `run-foundry-demo` skill.

## Layer Framing

Local-run failures fall into five layers, in this order of diagnosis:

1. **Console/encoding** — emoji or Unicode output crashes on Windows `cp1252`
2. **Process lifecycle** — servers do not start, do not become healthy, or do not shut down cleanly
3. **Auth/credential** — `DefaultAzureCredential` cannot get a token
4. **Model capability** — the chosen model does not support the tool the agent registers
5. **Runtime/wiring** — ports in use, env vars missing, async client misuse

Confirm the layer before diving deep. Most first-run failures on Windows are layer 1 or 2.

---

## Quick State Checks

Before changing any code, confirm the basics:

```bash
python --version
az account show --query "{name:name, user:user.name}" -o json
```

```bash
cat .env
.venv/Scripts/python -c "import a2a, openai, azure.ai.projects; print('imports ok')"
```

Confirm the model deployments the demo expects actually exist in the Foundry project:

```bash
az cognitiveservices account deployment list \
  --name <foundry-resource> --resource-group <rg> \
  --query "[].{name:name, model:properties.model.name}" -o table
```

---

## Triage Table

| Symptom | Layer | Likely cause | Where to fix |
|---|---|---|---|
| `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'` (or any emoji/Unicode) at startup | Console/encoding | Windows console / piped stdout defaults to `cp1252` | [UTF-8 output on Windows](#utf-8-output-on-windows) |
| Process exits non-zero, no `Goodbye!` / shutdown lines printed | Process lifecycle | `CTRL_BREAK_EVENT` sent to a subprocess in the parent's own process group, killing the launcher | [Clean subprocess shutdown on Windows](#clean-subprocess-shutdown-on-windows) |
| `Timeout waiting for server health at .../health` | Process lifecycle | Server crashed on import/startup; the crash is in the child's piped output | [Server fails health check](#server-fails-health-check) |
| Output stops mid-line, no traceback, garbled non-ASCII in child logs | Console/encoding | Subprocess stdout decoded with `cp1252` instead of UTF-8 | [UTF-8 output on Windows](#utf-8-output-on-windows) |
| `DefaultAzureCredential failed to retrieve a token` | Auth/credential | Not signed in, or wrong credential type enabled | Run `az login`; keep `exclude_environment_credential=True, exclude_managed_identity_credential=True` for local dev |
| Agent run errors only when the agent uses a `FunctionTool` (routing/host agent); leaf agents work | Model capability | The model does not support the Function tool in this region | Point the tool-using agent at a Function-capable model via a separate deployment var (e.g. `ROUTING_MODEL_DEPLOYMENT_NAME`) — see [Function tool model support](#function-tool-model-support) |
| `[Errno 10048] address already in use` / `error while attempting to bind on address` | Runtime/wiring | A previous run left a server on the port (10007/10008/10009 for A2A) | Re-use or stop the existing instance — see [Port already in use](#port-already-in-use) |
| `KeyError: 'PROJECT_ENDPOINT'` / `'SERVER_URL'` | Runtime/wiring | `.env` missing a var the script reads via `os.environ[...]` | Fill `.env` from `.env.example`; cross-reference `.claude/deploy.config` |
| Client appears to hang while the agent thinks | Runtime/wiring | `requests.post` is synchronous inside an async client — cosmetic for a single user, blocking under load | Acceptable for demos; switch to `httpx.AsyncClient` only if concurrency is needed |

---

## Operational Issues

### UTF-8 output on Windows

**Symptom:**

```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
```

**Cause:** When stdout is the Windows console (or is piped to a file/another process), Python encodes with the locale code page `cp1252`, which has no mapping for emoji (🚀 ✅ ❌ 🛑) or many Unicode punctuation marks the model emits (curly quotes, en dashes). This breaks both the launcher's own status prints and the streaming of child-server output.

**Fix — the launching script and any script that prints model output:**

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
```

**Fix — subprocesses whose output you stream** (`run_all.py` reading child stdout): decode the pipe as UTF-8 and tell the child to emit UTF-8:

```python
child_env = os.environ.copy()
child_env["PYTHONIOENCODING"] = "utf-8"
process = subprocess.Popen(
    cmd, env=child_env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding="utf-8", errors="replace",
)
```

`errors="replace"` keeps a single bad byte from killing the whole stream. This fix works both when run interactively in a VS Code terminal and when piped.

---

### Clean subprocess shutdown on Windows

**Symptom:** The demo produces correct output, but the process exits with a non-zero code and the final `Goodbye!` / `🛑 Stopping server subprocess...` lines never print. Servers may be left running.

**Cause:** To shut uvicorn down gracefully a launcher sends `CTRL_BREAK_EVENT`:

```python
process.send_signal(signal.CTRL_BREAK_EVENT)   # Windows path
```

On Windows, `CTRL_BREAK_EVENT` is delivered to the **process group**, not a single PID. If the child was created in the launcher's own group (the default), the break is broadcast back to the launcher — killing it before it can flush output and exit `0`.

**Fix:** Create each server subprocess in its own process group so the break reaches only the child:

```python
creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
process = subprocess.Popen(cmd, ..., creationflags=creationflags)
```

After the fix the launcher exits `0`, prints `Goodbye!`, and each uvicorn child logs `Application shutdown complete`. `process.terminate()` is a simpler but harder kill (no graceful uvicorn shutdown); prefer the process-group + `CTRL_BREAK_EVENT` approach when graceful child shutdown matters.

---

### Server fails health check

**Symptom:** The launcher prints `❌ Timeout waiting for server health at http://localhost:PORT/health` and exits.

**Cause:** The uvicorn child crashed during import or startup (bad env var, import error, agent-creation error in a FastAPI `lifespan`). The real traceback is in the **child's** stdout, which the launcher streams — scroll up past the timeout line.

**Diagnose:** Run the failing server directly to see the traceback uncaptured:

```bash
.venv/Scripts/python -m uvicorn title_agent.server:app --host localhost --port 10007 --log-level debug
```

Fix the underlying import/env/auth error, then re-run `run_all.py`.

---

### Function tool model support

**Symptom:** Leaf agents (no tools) run fine, but the routing/host agent that registers a `FunctionTool` in its `PromptAgentDefinition` errors at run time.

**Cause:** Not every Foundry model supports the **Function** tool in every region. Example seen in this repo: `gpt-5.4` does **not** support Function tools, while `gpt-5.2` does.

**Fix:** Keep the tool-using agent on its own deployment variable so it can differ from the leaf agents:

```bash
MODEL_DEPLOYMENT_NAME=gpt-5.4            # leaf agents, no tools
ROUTING_MODEL_DEPLOYMENT_NAME=gpt-5.2    # routing agent, Function-capable
```

Confirm support in [Tool support by region and model](https://learn.microsoft.com/azure/foundry/agents/concepts/tool-best-practice#tool-support-by-region-and-model).

---

### Port already in use

**Symptom:** `[Errno 10048] ... address already in use` when a server tries to bind.

**Cause:** A previous `run_all.py` run did not shut down cleanly (often the [shutdown bug](#clean-subprocess-shutdown-on-windows) above) and left a server holding the port. A2A demos use `10007` (title), `10008` (segment), `10009` (routing).

**Fix — find and stop the stale listener (Windows):**

```powershell
Get-NetTCPConnection -LocalPort 10007,10008,10009 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalPort, OwningProcess
Stop-Process -Id <pid> -Force
```

Per repo rules, prefer re-using a healthy running instance over starting a new one. Only kill a listener that is actually stale.

---

## Healthy Run Signature

A clean multi-server A2A run produces all of the following, in order:

1. `🚀 Starting <name> on port <port>` followed by `✅ <name> is healthy and ready!` for each of the three servers.
2. `Found remote agents: [ ... ]` from the routing agent, listing both leaf agents by card name.
3. `Routing agent initialized.`
4. `Agent: <composed answer>` — one user prompt yields a title-then-segments answer delegated across both leaf agents.
5. On `quit`: `Goodbye!`, then `🛑 Stopping server subprocess...`, then `Application shutdown complete` once per server, exit code `0`.

If steps 1-4 succeed but step 5 is missing, you have the [shutdown bug](#clean-subprocess-shutdown-on-windows), not a logic error — the agents worked.

---

## References

- [Tool support by region and model](https://learn.microsoft.com/azure/foundry/agents/concepts/tool-best-practice#tool-support-by-region-and-model)
- [DefaultAzureCredential](https://learn.microsoft.com/python/api/overview/azure/identity-readme#defaultazurecredential)
- [A2A protocol](https://learn.microsoft.com/training/modules/discover-agents-with-a2a/)
- [`io.TextIOWrapper.reconfigure`](https://docs.python.org/3/library/io.html#io.TextIOWrapper.reconfigure)
