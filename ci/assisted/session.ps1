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
# Roblox deploys Assistant as a built-in OTA plugin. A new disposable
# Windows runner can open the editor while this bundle is missing or still
# downloading. Log only generic file counts, never folder contents.
$assistantPluginRoot = Join-Path $env:LOCALAPPDATA 'Roblox\OTAPlugins\Deployed\BuiltInStandalonePlugins'
$assistantBundle = Join-Path $assistantPluginRoot 'Assistant.rbxm'
$assistantExists = Test-Path -LiteralPath $assistantBundle -PathType Leaf
Write-Host "MCP_ASSISTANT_PLUGIN_SAFE_DIAG: official_assistant_bundle_present=$assistantExists"
# The official Assistant may be delivered with Studio's signed version
# rather than an OTA patch. Check both locations and only print boolean
# status and safe error counts; never print Roblox logs or account data.
$assetDiag = (& python .\ci\assisted\probe-assistant-assets.py | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'ASSISTANT_ASSET_SAFE_PROBE_FAILED' }
Write-Host $assetDiag
# Roblox Studio developers recommend restarting Studio on plugin-load
# failures. A missing file in both known roots on an ephemeral runner
# justifies ONE bounded fresh-launch attempt; no cache deletion, account
# bypass, tampering with signed assets or persistent user games.
if ($assetDiag -match 'ota_present=false' -and $assetDiag -match 'version_present=false') {
    Write-Host 'ASSISTANT_BUNDLE_RECHECK: no official asset in known locations; one signed Studio restart.'
    Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 6
    Start-Process -FilePath $env:STUDIO_EXE | Out-Null
    Start-Sleep -Seconds 16
    # Relaunch only the same pinned local CI fixture via official EditFile.
    ./ci/assisted/open-test-place-cli.ps1
    if ($LASTEXITCODE -ne 0) {
        throw 'ASSISTANT_RECHECK_LOCAL_EDITOR_NOT_VERIFIED'
    }
    $assetDiagAfter = (& python .\ci\assisted\probe-assistant-assets.py | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'ASSISTANT_RECHECK_ASSET_PROBE_FAILED' }
    Write-Host "ASSISTANT_BUNDLE_RECHECK_RESULT: $assetDiagAfter"
}
$mcpBatch = Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat'
$mcpExe = Join-Path (Split-Path -Parent $env:STUDIO_EXE) 'StudioMCP.exe'
Write-Host "MCP_RUNTIME_SAFE_DIAG: official_launcher_present=$(Test-Path -LiteralPath $mcpBatch), installed_binary_present=$(Test-Path -LiteralPath $mcpExe)"
# An official launcher may already exist after Studio has authenticated.
# Never overwrite or fabricate one. If absent, enable it through Studio UI.
# If present, the following official tunnel doctor must still prove a live
# MCP handshake before declaring success.
if (-not (Test-Path -LiteralPath $mcpBatch)) {
    # Authenticated account's own Studio Assistant settings can persist MCP
    # enabled=true even when the newest built-in Assistant's UI is not
    # accessible in Windows UIA/DXGI. In a disposable hosted runner only,
    # prefer the exact account preference backed by Roblox's own setting
    # format. Roblox itself must then load it and produce mcp.bat.
    # This does not bypass login/MFA, replace StudioMCP.exe or fabricate the
    # launcher. Failures fall through to the official guarded UI path.
    $prefOutput = (& python .\ci\assisted\enable-official-mcp-preference.py | Out-String).Trim()
    $prefResult = $LASTEXITCODE
    if ($prefOutput) { Write-Host $prefOutput }
    if ($prefResult -eq 0) {
        Write-Host 'MCP_FIRST_PARTY_PREF_RESTART: reloading authenticated disposable Studio.'
        Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
        Start-Process -FilePath $env:STUDIO_EXE | Out-Null
        Start-Sleep -Seconds 15
        ./ci/assisted/open-test-place-cli.ps1
        if ($LASTEXITCODE -ne 0) { throw 'MCP_PREF_RESTART_BASEPLATE_NOT_VERIFIED' }
        Start-Sleep -Seconds 5
        Write-Host "MCP_FIRST_PARTY_PREF_RESTART_RESULT: official_launcher_present=$(Test-Path -LiteralPath $mcpBatch)"
    } else {
        Write-Host 'MCP_PREF_APPLY_UNAVAILABLE: retain official Assistant GUI-only fallback.'
    }
}
if (-not (Test-Path -LiteralPath $mcpBatch)) {
    Write-Host 'MCP_LAUNCHER_MISSING: enabling official Studio MCP from Assistant UI.'
    # OCR is local-only and used only on the signed-in, confirmed CI Baseplate
    # editor mezzanine. No image, extracted text, account data or OTP is logged.
    # The guarded Win32 tooltip fallback remains if optional OCR is unavailable.
    Write-Host 'MCP_VISUAL_RUNTIME: installing optional offline OCR for custom-drawn Assistant tooltip.'
    python -m pip install --disable-pip-version-check --quiet 'rapidocr==3.10.0' 'onnxruntime>=1.18,<2'
    if ($LASTEXITCODE -ne 0) { Write-Host 'MCP_VISUAL_RUNTIME_UNAVAILABLE: continuing with strict native tooltip-only fallback.' }
    python .\ci\assisted\activate-mcp-ui.py
    if ($LASTEXITCODE -ne 0) { throw 'Studio MCP enable control not reachable via UI automation.' }
} else {
    Write-Host 'MCP_OFFICIAL_LAUNCHER_ALREADY_PRESENT: validating via official tunnel doctor.'
}
if (-not (Test-Path -LiteralPath $mcpBatch)) { throw 'Studio MCP official launcher absent after UI check.' }
Write-Host 'Initializing a named OpenAI Secure MCP Tunnel stdio profile.'
# OpenAI documentation requires init --profile before run --profile.
# Keep the tunnel runtime API key in the inherited environment, not CLI args.
# The official OpenAI Go parser treats backslashes as escape characters
# in --mcp-command (and its cmd.exe arguments must survive *two* parsers).
# Using a command with NO quotes/backslashes avoids corrupting Windows
# paths. The tracked bridge calls ONLY Roblox's verified mcp.bat; it never
# writes or replaces that official launcher.
$bridge = Join-Path $env:GITHUB_WORKSPACE 'roblox-mcp-stdio.cmd'
if (-not (Test-Path -LiteralPath $bridge -PathType Leaf)) {
    throw 'STUDIO_MCP_STDIO_BRIDGE_NOT_FOUND'
}
# cmd.exe resolves the bridge from the process working directory.
# Pin it explicitly so the tunnel process launched in the NEXT Actions
# step uses the same location. No username or file path is logged.
Set-Location -LiteralPath $env:GITHUB_WORKSPACE
$mcpCommand = 'cmd.exe /d /c roblox-mcp-stdio.cmd'
Write-Host 'MCP_STDIO_BRIDGE_PROFILE_VERIFIED: quote_free_command=true official_launcher_required=true'
$profileName = 'roblox-studio-ci'
& $env:TUNNEL_EXE init --sample sample_mcp_stdio_local --profile $profileName --tunnel-id $env:CONTROL_PLANE_TUNNEL_ID --mcp-command $mcpCommand
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel profile initialization failed.' }
Write-Host 'Tunnel profile initialized. Running official doctor checks.'
& $env:TUNNEL_EXE doctor --profile $profileName --explain
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel doctor check failed.' }
# Expose the completed MCP+doctor setup as its own GitHub Actions step
# before starting an intentionally long-running foreground tunnel. This
# lets the next AI see precise stage completion while a tunnel is active.
if ($env:ROBLOX_MCP_SETUP_ONLY -eq '1') {
    Write-Host 'STUDIO_MCP_SETUP_AND_TUNNEL_DOCTOR_VERIFIED: stopping at completed setup gate.'
    exit 0
}
# The tunnel client's default auto-restart would hide a bad stdio child in
# thousands of repeated logs. Fail visibly, without looping on a broken
# Roblox-generated launcher; this does not interfere with healthy MCP sessions.
$env:MCP_STDIO_FAILURE_POLICY = 'exit'
Write-Host 'TUNNEL_STDIO_FAIL_FAST_ENABLED: unexpected child failure ends the tunnel process.'
Write-Host 'TUNNEL_STARTING: OpenAI Secure MCP Tunnel is connecting.'
& $env:TUNNEL_EXE run --profile $profileName
if ($LASTEXITCODE -ne 0) { throw 'OpenAI tunnel-client exited unsuccessfully.' }
