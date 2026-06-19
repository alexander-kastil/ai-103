$root = $PSScriptRoot
$coffee = Join-Path $root "mcp-coffee-py"
$qr = Join-Path $root "qr-server"

$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')

Write-Host "Setting up mcp-coffee-py environment..."
python -m venv "$coffee\.venv"
& "$coffee\.venv\Scripts\python.exe" -m pip install -r "$coffee\requirements.txt"
if (-not (Test-Path "$coffee\.env")) { Copy-Item "$coffee\.env.example" "$coffee\.env" }

Write-Host "Setting up qr-server environment..."
python -m venv "$qr\.venv"
& "$qr\.venv\Scripts\python.exe" -m pip install -r "$qr\requirements.txt"

Write-Host "Starting roastery MCP server on http://127.0.0.1:8000/mcp ..."
Start-Process -FilePath "$coffee\.venv\Scripts\python.exe" -ArgumentList "server.py", "--http" -WorkingDirectory $coffee

Write-Host "Starting QR MCP server on http://127.0.0.1:3001/mcp ..."
Start-Process -FilePath "$qr\.venv\Scripts\python.exe" -ArgumentList "server.py" -WorkingDirectory $qr

Write-Host "Signing in to dev tunnels..."
devtunnel user login

$log = Join-Path $env:TEMP "devtunnel-ai103.log"
if (Test-Path $log) { Remove-Item $log }
Write-Host "Hosting dev tunnel for ports 8000 and 3001 in a new terminal..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "devtunnel host -p 8000 -p 3001 --allow-anonymous *>&1 | Tee-Object -FilePath '$log'"
Start-Sleep -Seconds 8

$out = Get-Content $log -Raw
$roastery = [regex]::Match($out, 'https://\S*?-8000\.\S*?devtunnels\.ms').Value + "/mcp"
$qrUrl = [regex]::Match($out, 'https://\S*?-3001\.\S*?devtunnels\.ms').Value + "/mcp"

$envFile = "$coffee\.env"
$content = Get-Content $envFile
$content = $content -replace '^ROASTERY_MCP_URL=.*', "ROASTERY_MCP_URL=`"$roastery`""
$content = $content -replace '^QR_MCP_URL=.*', "QR_MCP_URL=`"$qrUrl`""
Set-Content -Path $envFile -Value $content
Write-Host "Wrote ROASTERY_MCP_URL=$roastery"
Write-Host "Wrote QR_MCP_URL=$qrUrl"

az account show *> $null
if ($LASTEXITCODE -ne 0) { az login }

Write-Host "Running the agent..."
& "$coffee\.venv\Scripts\python.exe" "$coffee\agent.py"
