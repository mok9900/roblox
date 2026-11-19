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
Write-Host 'Checking a uniquely labeled native Studio login form before browser fallback.'
# Try each verified sign-in mode only when the preceding mode did not
# enter any credentials. Never retry after an ambiguous/partial submission.
# The native Studio login form provides the most reliable, explicitly
# labeled official email-OTP challenge. Prefer it over a browser fallback.
# A brand-new runner sometimes displays a blank Studio welcome window;
# restart it ONCE before any secrets are submitted, then retry native UIA.
python .\ci\assisted\native-studio-login.py
$nativeResult = $LASTEXITCODE
if ($nativeResult -eq 10) {
    Write-Host 'PRE_CREDENTIAL_NATIVE_RESTART: no verified native fields; restart Studio once before considering browser.'
    Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 4
    Start-Process -FilePath $env:STUDIO_EXE | Out-Null
    Start-Sleep -Seconds 8
    python .\ci\assisted\native-studio-login.py
    $nativeResult = $LASTEXITCODE
}
if ($nativeResult -eq 10) {
    $env:ROBLOX_LOGIN_MODE = 'browser'
    Write-Host 'NATIVE_STUDIO_UNAVAILABLE_AFTER_RESTART: validating official URI handler before guarded Edge login.'
    ./ci/assisted/check-studio-auth-protocol.ps1 -RequireRegistered
    Write-Host 'STUDIO_BROWSER_OAUTH_SAFE_TO_START: Windows protocol handler and Edge allowlist configured.'
    python .\ci\assisted\visual-browser-login.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Visual Roblox browser sign-in failed closed; no blind credentials retry.'
    }
} elseif ($nativeResult -ne 0) {
    throw 'Native Studio login form failed safe validation; aborting without blind input.'
} else {
    $env:ROBLOX_LOGIN_MODE = 'native'
}
$env:ROBLOX_PRIMARY_SUBMITTED = '1'
Write-Host 'Continuing official Roblox app approval or encrypted Gmail 2FA.'
python .\ci\assisted\login-ui.py
if ($LASTEXITCODE -ne 0) { throw 'Roblox 2FA or Studio login verification not completed.' }
Write-Host 'Opening an isolated local Roblox-owned Baseplate fixture with official Studio EditFile CLI.'
./ci/assisted/open-test-place-cli.ps1
if ($LASTEXITCODE -ne 0) { throw 'Could not open local Baseplate test file after Roblox authentication.' }
$mcpBatch = Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat'
$mcpExe = Join-Path (Split-Path -Parent $env:STUDIO_EXE) 'StudioMCP.exe'
Write-Host "MCP_RUNTIME_SAFE_DIAG: official_launcher_present=$(Test-Path -LiteralPath $mcpBatch), installed_binary_present=$(Test-Path -LiteralPath $mcpExe)"
# An official launcher may already exist after Studio has authenticated.
# Never overwrite or fabricate one. If absent, enable it through Studio UI.
# If present, the following official tunnel doctor must still prove a live
# MCP handshake before declaring success.
if (-not (Test-Path -LiteralPath $mcpBatch)) {
    Write-Host 'MCP_LAUNCHER_MISSING: enabling official Studio MCP from Assistant UI.'
    python .\ci\assisted\activate-mcp-ui.py
    if ($LASTEXITCODE -ne 0) { throw 'Studio MCP enable control not reachable via UI automation.' }
} else {
    Write-Host 'MCP_OFFICIAL_LAUNCHER_ALREADY_PRESENT: validating via official tunnel doctor.'
}
if (-not (Test-Path -LiteralPath $mcpBatch)) { throw 'Studio MCP official launcher absent after UI check.' }
Write-Host 'Initializing a named OpenAI Secure MCP Tunnel stdio profile.'
# OpenAI documentation requires init --profile before run --profile.
# Keep the tunnel runtime API key in the inherited environment, not CLI args.
$mcpCommand = 'cmd.exe /d /s /c "cd /d ""%LOCALAPPDATA%\Roblox"" && call mcp.bat"'
$profileName = 'roblox-studio-ci'
& $env:TUNNEL_EXE init --sample sample_mcp_stdio_local --profile $profileName --tunnel-id $env:CONTROL_PLANE_TUNNEL_ID --mcp-command $mcpCommand
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel profile initialization failed.' }
Write-Host 'Tunnel profile initialized. Running official doctor checks.'
& $env:TUNNEL_EXE doctor --profile $profileName --explain
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel doctor check failed.' }
Write-Host 'TUNNEL_STARTING: OpenAI Secure MCP Tunnel is connecting.'
& $env:TUNNEL_EXE run --profile $profileName
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel-client exited unsuccessfully.' }
