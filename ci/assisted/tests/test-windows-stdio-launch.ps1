# Runs WITHOUT any Roblox account, Studio installation, tunnel key or OTP.
# It validates Windows cmd.exe stdio handoff under a path with spaces while
# respecting the rule never to create a fake Roblox mcp.bat.
$ErrorActionPreference = 'Stop'
if (-not $env:GITHUB_ACTIONS -or $env:GITHUB_ACTIONS -ne 'true') {
    throw 'HOSTED_WINDOWS_TEST_ONLY'
}
$bridge = Join-Path (Resolve-Path '.').Path 'roblox-mcp-stdio.cmd'
if (-not (Test-Path -LiteralPath $bridge -PathType Leaf)) {
    throw 'STDIO_BRIDGE_MISSING'
}
$raw = Get-Content -LiteralPath $bridge -Raw
if ($raw -notmatch '(?i)call\s+"%LOCALAPPDATA%\\Roblox\\mcp\.bat"') {
    throw 'STDIO_BRIDGE_NOT_POINTING_TO_OFFICIAL_LAUNCHER'
}
if ($raw -match '(?i)\b(echo|copy|move|type)\s+.*mcp\.bat') {
    throw 'STDIO_BRIDGE_MUST_NEVER_GENERATE_OFFICIAL_LAUNCHER'
}
$working = Join-Path $env:RUNNER_TEMP ('safe stdio smoke ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $working -Force | Out-Null
try {
    $target = Join-Path $working 'safe-probe-child.cmd'
    $dispatcher = Join-Path $working 'safe-probe-dispatch.cmd'
    Set-Content -LiteralPath $target -Encoding Ascii -Value @(
        '@echo off'
        'echo SAFE_STDIO_CHILD_STARTED'
        'exit /b 0'
    )
    Set-Content -LiteralPath $dispatcher -Encoding Ascii -Value @(
        '@echo off'
        'if not defined STUDIO_PROBE_DIR exit /b 4'
        'cd /d "%STUDIO_PROBE_DIR%"'
        'if errorlevel 1 exit /b 5'
        'call "%STUDIO_PROBE_DIR%\safe-probe-child.cmd"'
        'exit /b %ERRORLEVEL%'
    )
    $env:STUDIO_PROBE_DIR = $working
    $env:STUDIO_PROBE_WORKDIR = $working
    # Python subprocess on Windows uses CreateProcessW with argv, as the Go
    # tunnel-client exec.Command does. No account data or public network.
    @'
import os, subprocess
p = subprocess.run(["cmd.exe", "/d", "/c", "safe-probe-dispatch.cmd"],
                   cwd=os.environ["STUDIO_PROBE_WORKDIR"],
                   capture_output=True, text=True, timeout=10)
if p.returncode != 0 or p.stdout.strip() != "SAFE_STDIO_CHILD_STARTED":
    raise SystemExit("STDIO_WINDOWS_CREATEPROCESS_CMD_DISPATCH_FAILED")
print("STDIO_WINDOWS_CREATEPROCESS_CMD_DISPATCH_VERIFIED")
'@ | python -
    if ($LASTEXITCODE -ne 0) { throw 'STDIO_WINDOWS_ARGV_SMOKE_FAILED' }
    # GitHub's own feature+main workflow invokes the child from repo CWD.
    $command = 'cmd.exe /d /c roblox-mcp-stdio.cmd'
    if ($command -match '["\\\x27%&|]' -or $command.Split(' ').Count -ne 4) {
        throw 'STDIO_TUNNEL_COMMAND_NOT_SHLEX_SAFE'
    }
    Write-Host 'STDIO_TUNNEL_SHLEX_SAFE_COMMAND_VERIFIED'
} finally {
    Remove-Item Env:STUDIO_PROBE_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:STUDIO_PROBE_WORKDIR -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $working -Recurse -Force -ErrorAction SilentlyContinue
}
