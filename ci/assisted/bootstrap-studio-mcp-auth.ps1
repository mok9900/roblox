# Prime Roblox's OFFICIAL StudioMCP auth token before Studio's final restart.
# GitHub-hosted Windows only; never copy, print, modify, or disable token checks.
param([int]$TimeoutSeconds = 25)
$ErrorActionPreference = 'Stop'

if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'MCP_AUTH_BOOTSTRAP_HOSTED_WINDOWS_ONLY'
}
if (-not $env:LOCALAPPDATA -or -not $env:GITHUB_WORKSPACE) {
    throw 'MCP_AUTH_BOOTSTRAP_ENV_MISSING'
}
$launcher = Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat'
$bridge = Join-Path $env:GITHUB_WORKSPACE 'roblox-mcp-stdio.cmd'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'MCP_AUTH_BOOTSTRAP_OFFICIAL_LAUNCHER_MISSING'
}
if (-not (Test-Path -LiteralPath $bridge -PathType Leaf)) {
    throw 'MCP_AUTH_BOOTSTRAP_STDIO_BRIDGE_MISSING'
}
# This is an official Roblox file created by StudioMCP.exe, not a user-managed secret.
# Never read, echo, copy or write its CONTENTS.
$token = Join-Path $env:LOCALAPPDATA 'Roblox\StudioMCP\auth.token'
function Test-OfficialTokenReady {
    if (-not (Test-Path -LiteralPath $token -PathType Leaf)) { return $false }
    return ((Get-Item -LiteralPath $token).Length -ge 32)
}
$present = Test-OfficialTokenReady
Write-Host "MCP_AUTH_TOKEN_BEFORE_BOOTSTRAP: present=$present"
if (-not $present) {
    if (@(Get-Process -Name 'StudioMCP' -ErrorAction SilentlyContinue).Count -gt 0) {
        throw 'MCP_AUTH_BOOTSTRAP_EXISTING_SERVER_WITHOUT_TOKEN'
    }
    # Start the REAL checked-in bridge -> REAL Roblox-generated mcp.bat.
    # Keeping stdin open permits the official stdio process to write its token.
    # stdout/stderr are never copied to the GitHub log.
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = (Join-Path $env:SystemRoot 'System32\cmd.exe')
    $start.Arguments = '/d /c roblox-mcp-stdio.cmd'
    $start.WorkingDirectory = $env:GITHUB_WORKSPACE
    $start.UseShellExecute = $false
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.CreateNoWindow = $true
    $proc = [System.Diagnostics.Process]::Start($start)
    if (-not $proc) { throw 'MCP_AUTH_BOOTSTRAP_CHILD_NOT_STARTED' }
    try {
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while ((Get-Date) -lt $deadline) {
            if (Test-OfficialTokenReady) { break }
            if ($proc.HasExited) { break }
            Start-Sleep -Milliseconds 500
        }
    } finally {
        try {
            if (-not $proc.HasExited) {
                $proc.Kill($true)
                [void]$proc.WaitForExit(5000)
            }
        } catch {
            # A child that exited between the check and Kill is already stopped.
            if (-not $proc.HasExited) { throw 'MCP_AUTH_BOOTSTRAP_CHILD_CLEANUP_FAILED' }
        } finally {
            $proc.Dispose()
        }
    }
}
if (-not (Test-OfficialTokenReady)) {
    throw 'MCP_AUTH_BOOTSTRAP_OFFICIAL_TOKEN_NOT_CREATED'
}
Write-Host 'MCP_AUTH_TOKEN_PRIMED: present=true official_launcher=true token_enforcement_unchanged=true'
