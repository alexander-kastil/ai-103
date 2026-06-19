# Lessons Learned

## MCP Server: pin mcp<2.0 when using uvx --prerelease

When `uvx --prerelease=allow` is used, it can pull in `mcp` v2 prerelease which removed `mcp.server.fastmcp`. Any server that does `from mcp.server.fastmcp import FastMCP` will fail.

Fix in `.mcp.json`: add `"--with", "mcp>=1.0,<2.0"` to the args array before the entrypoint command.

## MCP Server secrets: use --envFile, not inline env in .mcp.json

`.mcp.json` is tracked by git. Never embed API keys or secrets in the `env` block.

Pattern: pass `"--envFile", "<absolute-path-to-secrets-file>"` as args (requires the server to support `--envFile`, as `mcp-foundry` does). Store secrets in `.claude/deploy.config` and git-exclude that file via `.git/info/exclude`.

## Git-exclude local secrets with .git/info/exclude

For files that must exist locally but must never be committed, add them to `.git/info/exclude` (repo-local, not tracked). Do not add secrets to `.gitignore` (which is tracked).

## Azure AI Search free tier is valid for Foundry IQ demos

The readme explicitly says "Free (or Basic) tier". Free tier supports agentic retrieval knowledge bases when set up through the Foundry portal. Use `--sku free` in `az search service create`.

## az role assignment create fails in Claude Code Bash tool

`az role assignment create` with `--scope` returns "MissingSubscription" in the Bash tool even after `az account set`. Use PowerShell instead. In a real user terminal, the Bash command works fine.

## Demo folder naming and readme style

Runnable Python demo folders follow the `*-py` convention and share a consistent prefix when related (e.g. `store-ops-agent-py` + `store-ops-workiq-py`, not `base-agent` + `workiq-demo-py`). Demo readmes must have no em dashes and no version noise like "(version 1)". Renaming a folder means updating every reference: in-script error strings, `readme.md` links, `state.md`, and `tasks/handoff.md`. Moving a folder breaks its `.venv` (hardcoded absolute paths), so delete and recreate the venv after a move.

## claude mcp restart is not a valid command

To reload an MCP server after fixing `.mcp.json`, the user must restart the Claude Code session. There is no `claude mcp restart` subcommand.

## Provision/deprovision scripts belong in the demo parent folder

For demos that need Azure resources, create `provision.azcli` and `deprovision.azcli` in the demo's module folder (e.g., `modules/02-agents/04-foundry-iq/`), not inside the `*-py/` subfolder. These scripts handle the full resource lifecycle independently of the Python client setup.

## foundry-expert "not found" = the registry was frozen at session start, not a file problem

(The agent was renamed `maf-expert` → `foundry-expert` on 2026-06-18; the same reload rule applies to the new name.)

Subagents are loaded into the Agent-tool registry once, at session startup. Editing, renaming, or creating `.claude/agents/foundry-expert.md` mid-session does nothing for the running session, so retrying in the same session always fails with "Agent type not found". The file is valid; the cause is the in-session reload.

Durable fix applied: the agent lives at user level `~/.claude/agents/foundry-expert.md` so it loads in every session regardless of launch directory. Still requires a session restart to take effect; verify with `/agents` (should appear under Project/Personal agents).

Stopgap only when a restart is not possible: use a `general-purpose` agent and have it invoke the `microsoft-agent-framework` skill first (same Foundry/MAF knowledge base). Do not re-explain this to the user each time; it is a known, fixed issue.

## state.md should show only remaining work

Keep `state.md` as a live status board — blockers and next steps only. Remove completed items rather than accumulating a history log. History belongs in git commits.

## Windows demos must force UTF-8 stdout or emoji prints crash

Demos that print emojis (🚀 ✅ ❌ 🛑) or model output crash on Windows with `UnicodeEncodeError: 'charmap' codec can't encode character` because stdout defaults to `cp1252` when run in the console or piped. Add `sys.stdout.reconfigure(encoding="utf-8")` (and `sys.stderr` for the launcher) at the top of any script that prints them. For launchers that stream subprocess output, also spawn children with `encoding="utf-8"`, `errors="replace"`, and `PYTHONIOENCODING=utf-8` in the child env. Full guide: `.claude/skills/microsoft-agent-framework/references/agent-framework-run-troubleshooting.md`.

## Multi-server launchers need CREATE_NEW_PROCESS_GROUP on Windows

A launcher (`run_all.py`) that shuts uvicorn children down with `process.send_signal(signal.CTRL_BREAK_EVENT)` must create those children with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` on Windows. Otherwise the break is delivered to the launcher's own process group and kills the launcher before it flushes output — the demo runs correctly but exits non-zero with no `Goodbye!`/shutdown lines and may orphan servers on their ports. Verified on the A2A demo (`modules/02-agents/09-a2a`).
