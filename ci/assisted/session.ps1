$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if (-not $env:ROBLOX_USERNAME -or -not $env:ROBLOX_PASSWORD) {
    throw 'Missing ROBLOX_USERNAME or ROBLOX_PASSWORD GitHub Actions secrets.'
}
if (-not $env:CONTROL_PLANE_API_KEY -or -not $env:CONTROL_PLANE_TUNNEL_ID) {
    throw 'Missing OPENAI_TUNNEL_RUNTIME_KEY or OPENAI_TUNNEL_ID GitHub Actions secrets.'
}
if (-not $env:STUDIO_EXE -or -not (Test-Path $env:STUDIO_EXE)) { throw 'Studio executable missing.' }
if (-not $env:TUNNEL_EXE -or -not (Test-Path $env:TUNNEL_EXE)) { throw 'OpenAI tunnel executable missing.' }
$active = @(Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue)
if ($active.Count -eq 0) {
    Write-Host 'Launching installed Roblox Studio GUI.'
    Start-Process -FilePath $env:STUDIO_EXE | Out-Null
}
Write-Host 'Installing Windows UI Automation'
python -m pip install --disable-pip-version-check --quiet 'pywinauto==0.6.9'
if ($LASTEXITCODE -ne 0) { throw 'Unable to install Windows UI Automation.' }
Write-Host 'Attempting authorized Roblox GUI sign-in.'
python .\ci\assisted\login-ui.py
if ($LASTEXITCODE -ne 0) { throw 'Roblox GUI sign-in not verified (different UI or additional user action needed).' }
Write-Host 'Enabling the Studio MCP toggle through the official UI.'
python .\ci\assisted\activate-mcp-ui.py
if ($LASTEXITCODE -ne 0) { throw 'Studio MCP enable control not reachable via UI automation.' }
$mcpBatch = Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat'
if (-not (Test-Path $mcpBatch)) { throw 'Studio MCP launcher not found after GUI activation.' }
Write-Host 'Launching OpenAI outbound-only Secure MCP Tunnel. No inbound public port opened.'
Write-Host 'Keep the Actions job running while ChatGPT discovers or calls tools.'
$mcpCommand = 'cmd.exe /c "%LOCALAPPDATA%\Roblox\mcp.bat"'
& $env:TUNNEL_EXE run --mcp-command $mcpCommand --health.listen-addr 127.0.0.1:8080
if ($LASTEXITCODE -ne 0) { throw 'Tunnel client exited unsuccessfully.' }
