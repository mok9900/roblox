# No-auth, GitHub-managed Windows regression for the OpenAI tunnel health sampler.
# Validate source and PowerShell syntax; do not launch a tunnel or use credentials.
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'TUNNEL_HEALTH_TEST_HOSTED_WINDOWS_ONLY'
}
$path='ci/assisted/tunnel-health-probe.ps1'
$tokens=$null
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path $path).Path,[ref]$tokens,[ref]$errors) | Out-Null
if ($errors.Count -gt 0) {throw 'TUNNEL_HEALTH_POWERSHELL_PARSE_INVALID'}
$s=Get-Content -LiteralPath $path -Raw
foreach($fragment in @(
    'http://127.0.0.1:8080',
    '/readyz',
    '/health/control-plane',
    '/health/mcp',
    'Safe-Enum',
    'Safe-Counters',
    'body and exception redacted',
    'TUNNEL_LOCAL_HEALTH:'
)) {
    if (-not $s.Contains($fragment)) {throw 'TUNNEL_HEALTH_REQUIRED_SANITIZER_OR_ROUTE_MISSING'}
}
if ($s -match '(?i)Write-Host\s+\$plane\b|Write-Host\s+\$mcp\b|ConvertTo-Json|Set-Content|Out-File|Get-Content\s+[^\r\n]*auth\.token') {
    throw 'TUNNEL_HEALTH_MUST_NOT_PRINT_RAW_DATA_OR_STORE_TOKENS'
}
Write-Host 'TUNNEL_LOCAL_HEALTH_WINDOWS_SYNTAX_AND_SANITIZATION_SOURCE_VERIFIED'
