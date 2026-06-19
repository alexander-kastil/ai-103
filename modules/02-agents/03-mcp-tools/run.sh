#!/usr/bin/env bash
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
coffee="$root/mcp-coffee-py"
qr="$root/qr-server"

echo "Setting up mcp-coffee-py environment..."
python3 -m venv "$coffee/.venv"
"$coffee/.venv/bin/python" -m pip install -r "$coffee/requirements.txt"
[ -f "$coffee/.env" ] || cp "$coffee/.env.example" "$coffee/.env"

echo "Setting up qr-server environment..."
python3 -m venv "$qr/.venv"
"$qr/.venv/bin/python" -m pip install -r "$qr/requirements.txt"

echo "Starting roastery MCP server on http://127.0.0.1:8000/mcp ..."
( cd "$coffee" && "$coffee/.venv/bin/python" server.py --http ) &

echo "Starting QR MCP server on http://127.0.0.1:3001/mcp ..."
( cd "$qr" && "$qr/.venv/bin/python" server.py ) &

echo "Signing in to dev tunnels..."
devtunnel user login

log="$(mktemp)"
echo "Hosting dev tunnel for ports 8000 and 3001..."
devtunnel host -p 8000 -p 3001 --allow-anonymous > "$log" 2>&1 &
sleep 6

roastery="$(grep -oE 'https://[^[:space:]]*-8000\.[^[:space:]]*devtunnels\.ms' "$log" | head -1)/mcp"
qr_url="$(grep -oE 'https://[^[:space:]]*-3001\.[^[:space:]]*devtunnels\.ms' "$log" | head -1)/mcp"

envfile="$coffee/.env"
tmp="$(mktemp)"
sed -e "s|^ROASTERY_MCP_URL=.*|ROASTERY_MCP_URL=\"$roastery\"|" \
    -e "s|^QR_MCP_URL=.*|QR_MCP_URL=\"$qr_url\"|" "$envfile" > "$tmp"
mv "$tmp" "$envfile"
echo "Wrote ROASTERY_MCP_URL=$roastery"
echo "Wrote QR_MCP_URL=$qr_url"

az account show >/dev/null 2>&1 || az login

echo "Running the agent..."
"$coffee/.venv/bin/python" "$coffee/agent.py"
