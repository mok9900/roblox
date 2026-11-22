# Credential-free official GitHub-hosted Windows auth-token priming regression.
# This never starts Roblox Studio/MCP and never creates a fake mcp.bat/token.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'MCP_AUTH_PRIMING_TEST_REQUIRES_HOSTED_WINDOWS'
}
$helper = 'ci/assisted/bootstrap-studio-mcp-auth.ps1'
$session = 'ci/assisted/session.ps1'
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path $helper).Path, [ref]$tokens, [ref]$errors
) | Out-Null
if ($errors.Count -gt 0) { throw 'MCP_AUTH_PRIMING_POWERSHELL_PARSE_FAILED' }

$src = Get-Content -LiteralPath $helper -Raw
if (-not $src.Contains('Roblox\StudioMCP\auth.token') -or
    -not $src.Contains('roblox-mcp-stdio.cmd') -or
    -not $src.Contains('Test-OfficialTokenReady') -or
    -not $src.Contains('$proc.Kill($true)')) {
    throw 'MCP_AUTH_PRIMING_OFFICIAL_TOKEN_CHILD_GUARDS_MISSING'
}
if ($src -match '(?i)FFlagStudioMCPProxyTokenEnforce|Set-Content\s.*auth\.token|Copy-Item\s.*auth\.token|Out-File\s.*auth\.token') {
    throw 'MCP_AUTH_PRIMING_MUST_NOT_DISABLE_OR_REPLACE_AUTH'
}
$sessionSrc = Get-Content -LiteralPath $session -Raw
$bootstrap = $sessionSrc.IndexOf('./ci/assisted/bootstrap-studio-mcp-auth.ps1')
$restart = $sessionSrc.IndexOf('MCP_AUTH_TOKEN_STUDIO_RESTART')
$profile = $sessionSrc.IndexOf("Initializing a named OpenAI Secure MCP Tunnel stdio profile.")
if ($bootstrap -lt 0 -or $restart -le $bootstrap -or $profile -le $restart) {
    throw 'MCP_AUTH_PRIMING_WRONG_SEQUENCE'
}
Write-Host 'MCP_AUTH_PRIMING_POWERSHELL_PARSE_AND_ORDER_VERIFIED'
# Execute only fail-closed with an empty synthetic AppData root.
$fake = Join-Path $env:RUNNER_TEMP ('empty mcp appdata ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fake -Force | Out-Null
$old = $env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA = $fake
    $thrown = $false
    try {
        & $helper -TimeoutSeconds 1
    } catch {
        $thrown = $true
        if ($_.Exception.Message -notmatch 'MCP_AUTH_BOOTSTRAP_OFFICIAL_LAUNCHER_MISSING') {
            throw 'MCP_AUTH_PRIMING_WRONG_FAIL_CLOSED_REASON'
        }
    }
    if (-not $thrown) { throw 'MCP_AUTH_PRIMING_SHOULD_FAIL_WITHOUT_ROBLOX_LAUNCHER' }
    if (Test-Path -LiteralPath (Join-Path $fake 'Roblox\StudioMCP\auth.token')) {
        throw 'MCP_AUTH_PRIMING_MUST_NOT_FABRICATE_TOKEN'
    }
    Write-Host 'MCP_AUTH_PRIMING_EMPTY_APPDATA_FAIL_CLOSED_VERIFIED'
} finally {
    $env:LOCALAPPDATA = $old
    Remove-Item -LiteralPath $fake -Recurse -Force -ErrorAction SilentlyContinue
}
