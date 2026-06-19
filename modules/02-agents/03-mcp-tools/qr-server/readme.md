# QR Code MCP Server

A standalone MCP server that generates QR codes from URLs and text. It runs over **stdio** (for GitHub Copilot, Claude Desktop, etc.) or **streamable HTTP** (for web and cloud clients), and is reused as a third **custom** MCP server in the [MCP tools demo](../readme.md).

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
# or with uv: uv run server.py --stdio
```

## Transports

```bash
# HTTP mode (default) — serves at http://0.0.0.0:3001/mcp, stateless
python server.py

# stdio mode — for GitHub Copilot, Claude Desktop, and other stdio MCP clients
python server.py --stdio
```

The HTTP port is configurable via the `PORT` environment variable (default `3001`).

## Test with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser-based tool for exercising an MCP server's tools and resources directly. It needs **Node.js** on the PATH (`npx`); the server itself stays Python. A ready-made [`inspector.config.json`](inspector.config.json) defines two named servers — `qr-code-stdio` and `qr-code-http`.

**stdio** (Inspector launches the server with `uv`, which installs the inline dependencies):

```bash
npx @modelcontextprotocol/inspector --config inspector.config.json --server qr-code-stdio
```

**Streamable HTTP** (start the server first, then connect Inspector to it):

```bash
python server.py
npx @modelcontextprotocol/inspector --config inspector.config.json --server qr-code-http
```

In the Inspector UI, open **Tools → `generate_qr`**, set `text` to `https://www.integrations.at`, and run it — the returned `ImageContent` renders as the QR PNG. The `ui://qr-server/view.html` entry appears under **Resources**.

## Use in GitHub Copilot

1. Open Copilot Chat (Ctrl+L)
2. Switch to **Agent** mode
3. Ask: `Generate a QR code for https://www.integrations.at`

The MCP server is configured in `.vscode/mcp.json` and will be automatically available.

## Use with the Foundry agent demo

The [MCP tools demo](../readme.md) attaches this server to a Foundry agent as the `qr-code` MCP tool, alongside the remote Microsoft Learn server and the local roastery server. Because the Foundry service calls the tool from the cloud, run this server over HTTP and expose it with a dev tunnel:

```bash
python server.py
devtunnel host -p 3001 --allow-anonymous
```

Then set `QR_MCP_URL` in the demo's `.env` to the tunnel URL with the `/mcp` path appended. The [`run.ps1`/`run.sh`](../) scripts in the demo folder automate the environment setup and start this server for you.

## Parameters

- `text` - URL or text to encode (required)
- `box_size` - Size in pixels (default: 5)
- `border` - Border size (default: 4)
- `error_correction` - Level: L/M/Q/H (default: M)
- `fill_color` - Foreground color (default: black)
- `back_color` - Background color (default: white)
