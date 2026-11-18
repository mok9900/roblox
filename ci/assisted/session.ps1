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
Write-Host 'Installing DXGI screen capture, Windows UI Automation, and SendInput support.'
python -m pip install --disable-pip-version-check --quiet 'pywinauto==0.6.9' 'psutil>=6.1,<8' 'dxcam[winrt]==0.2.0' 'Pillow>=11,<13'
if ($LASTEXITCODE -ne 0) { throw 'Unable to install safe Windows GUI automation dependencies.' }
Write-Host 'Priming Microsoft Edge renderer accessibility BEFORE activating Studio.'
./ci/assisted/prime-edge.ps1
$active = @(Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue)
if ($active.Count -eq 0) {
    Write-Host 'Launching installed Roblox Studio GUI after Edge priming.'
    Start-Process -FilePath $env:STUDIO_EXE | Out-Null
}
Start-Sleep -Seconds 3
Write-Host 'Using in-memory WGC/DXGI to identify Studio login CTA; submitting secrets only to verified Roblox Edge form.'
python .\ci\assisted\visual-browser-login.py
if ($LASTEXITCODE -ne 0) { throw 'Visual Roblox browser sign-in failed closed (no fallback to blind credential input).' }
$env:ROBLOX_PRIMARY_SUBMITTED = '1'
Write-Host 'Continuing official Roblox app approval or encrypted Gmail 2FA.'
python .\ci\assisted\login-ui.py
if ($LASTEXITCODE -ne 0) { throw 'Roblox 2FA or Studio login verification not completed.' }
Write-Host 'Opening an isolated local Roblox-owned Baseplate fixture with official Studio EditFile CLI.'
./ci/assisted/open-test-place-cli.ps1
if ($LASTEXITCODE -ne 0) { throw 'Could not open local Baseplate test file after Roblox authentication.' }
Write-Host 'Enabling the Studio MCP toggle through the official UI.'
python .\ci\assisted\activate-mcp-ui.py
if ($LASTEXITCODE -ne 0) { throw 'Studio MCP enable control not reachable via UI automation.' }
$mcpBatch = Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat'
if (-not (Test-Path $mcpBatch)) { throw 'Studio MCP launcher not found after GUI activation.' }
Write-Host 'Initializing a named OpenAI Secure MCP Tunnel stdio profile.'
# OpenAI documentation requires init --profile before run --profile.
# Keep the tunnel runtime API key in the inherited environment, not CLI args.
$mcpCommand = 'cmd.exe /c "%LOCALAPPDATA%\Roblox\mcp.bat"'
$profileName = 'roblox-studio-ci'
& $env:TUNNEL_EXE init --sample sample_mcp_stdio_local --profile $profileName --tunnel-id $env:CONTROL_PLANE_TUNNEL_ID --mcp-command $mcpCommand
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel profile initialization failed.' }
Write-Host 'Tunnel profile initialized. Running official doctor checks.'
& $env:TUNNEL_EXE doctor --profile $profileName --explain
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel doctor check failed.' }
Write-Host 'TUNNEL_STARTING: OpenAI Secure MCP Tunnel is connecting.'
& $env:TUNNEL_EXE run --profile $profileName
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel-client exited unsuccessfully.' }
