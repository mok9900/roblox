# Reuse a user-approved signed-in interactive Studio desktop.
# No Roblox credentials or OTP relay are consumed by this entrypoint.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (-not $env:CONTROL_PLANE_API_KEY -or -not $env:CONTROL_PLANE_TUNNEL_ID) {
    throw 'PERSISTENT_TUNNEL_SECRETS_MISSING: OPENAI_TUNNEL_RUNTIME_KEY and OPENAI_TUNNEL_ID are required.'
}
if (-not $env:STUDIO_EXE -or -not (Test-Path -LiteralPath $env:STUDIO_EXE)) {
    throw 'PERSISTENT_STUDIO_EXE_MISSING: install signed Studio for this Windows user.'
}
if (-not $env:TUNNEL_EXE -or -not (Test-Path -LiteralPath $env:TUNNEL_EXE)) {
    throw 'PERSISTENT_TUNNEL_EXE_MISSING: official tunnel-client is required.'
}
if (-not $env:LOCALAPPDATA) { throw 'PERSISTENT_WINDOWS_USER_PROFILE_MISSING' }

# A Windows service session cannot control the user's existing desktop.
# Unlike the throwaway hosted runner, this mode MUST run from run.cmd
# in the currently logged-in, interactive Windows account.
$interactiveCheck = @'
import ctypes
import sys
u = ctypes.windll.user32
if not u.GetForegroundWindow() or u.GetSystemMetrics(0) < 640 or u.GetSystemMetrics(1) < 480:
    print("PERSISTENT_INTERACTIVE_DESKTOP_NOT_FOUND")
    sys.exit(12)
print("PERSISTENT_INTERACTIVE_DESKTOP_READY")
'@
$interactiveCheck | python -
if ($LASTEXITCODE -ne 0) { throw 'PERSISTENT_RUNNER_MUST_BE_INTERACTIVE: start actions runner via run.cmd, NOT as a Windows service.' }

Write-Host 'PERSISTENT_SESSION: reusing approved Windows Studio sign-in; no credentials or email OTP submitted.'
python -m pip install --disable-pip-version-check --quiet 'pywinauto==0.6.9' 'psutil>=6.1,<8' 'dxcam[winrt]==0.2.0' 'Pillow>=11,<13'
if ($LASTEXITCODE -ne 0) { throw 'PERSISTENT_GUI_DEPENDENCY_INSTALL_FAILED' }

# Opening a pinned, local-only fixture is safe: it never modifies or
# publishes any existing Roblox experience. Existing Studio login is reused.
./ci/assisted/open-test-place-cli.ps1
if ($LASTEXITCODE -ne 0) {
    throw 'PERSISTENT_STUDIO_EDITOR_UNVERIFIED: sign in once using the official interactive Studio UI, then retry. No OTP bypass attempted.'
}
$launcher = Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat'
$studioMcpExe = Join-Path (Split-Path -Parent $env:STUDIO_EXE) 'StudioMCP.exe'
Write-Host "PERSISTENT_MCP_CHECK: official_launcher=$(Test-Path -LiteralPath $launcher), studio_binary=$(Test-Path -LiteralPath $studioMcpExe)"
if (-not (Test-Path -LiteralPath $launcher)) {
    Write-Host 'PERSISTENT_MCP_TOGGLE_REQUIRED: official Assistant > Settings > MCP Servers > Enable Studio as MCP server.'
    python -m pip install --disable-pip-version-check --quiet 'rapidocr==3.10.0' 'onnxruntime>=1.18,<2'
    if ($LASTEXITCODE -ne 0) { Write-Host 'PERSISTENT_OPTIONAL_OCR_UNAVAILABLE: native UIA fallback only.' }
    python ./ci/assisted/activate-mcp-ui.py
    if ($LASTEXITCODE -ne 0) {
        throw 'PERSISTENT_MCP_UI_UNREACHABLE: enable official switch in the already-open Studio Assistant and rerun.'
    }
}
if (-not (Test-Path -LiteralPath $launcher)) {
    throw 'PERSISTENT_OFFICIAL_MCP_LAUNCHER_MISSING: do not synthesize or overwrite mcp.bat.'
}

# Make Studio's documented batch launcher run from its own directory.
# This avoids command-processor working-directory errors and preserves
# the exact official launcher. The browser/Studio OAuth URL is never logged.
$mcpCommand = 'cmd.exe /d /s /c "cd /d ""%LOCALAPPDATA%\Roblox"" && call mcp.bat"'
$profileName = 'roblox-studio-persistent'
& $env:TUNNEL_EXE init --sample sample_mcp_stdio_local --profile $profileName --tunnel-id $env:CONTROL_PLANE_TUNNEL_ID --mcp-command $mcpCommand
if ($LASTEXITCODE -ne 0) { throw 'PERSISTENT_TUNNEL_INIT_FAILED' }
Write-Host 'PERSISTENT_TUNNEL_DOCTOR: invoking official local and tunnel readiness checks.'
& $env:TUNNEL_EXE doctor --profile $profileName --explain
if ($LASTEXITCODE -ne 0) { throw 'PERSISTENT_TUNNEL_DOCTOR_FAILED' }
Write-Host 'PERSISTENT_TUNNEL_RUN: client starting; use list_roblox_studios from ChatGPT to prove handshake.'
& $env:TUNNEL_EXE run --profile $profileName
if ($LASTEXITCODE -ne 0) { throw 'PERSISTENT_TUNNEL_RUN_EXITED' }
