# Privacy-safe, read-only health sampling for the official OpenAI tunnel-client.
# Run in parallel with 'tunnel-client run' on a GitHub-hosted Windows runner.
# Never print JSON bodies, names, file paths, identifiers, headers, tool lists,
# tunnel IDs, credentials, account data, or raw exception messages.
param(
    [ValidateRange(1, 30)][int]$Samples = 12,
    [ValidateRange(2, 60)][int]$IntervalSeconds = 10
)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'TUNNEL_HEALTH_DIAG_HOSTED_WINDOWS_ONLY'
}
$base = 'http://127.0.0.1:8080'
function Safe-Enum([object]$value) {
    $s = [string]$value
    if ($s -cmatch '^[a-z][a-z0-9_]{0,31}$') { return $s }
    return 'unknown'
}
function Safe-Counters([object]$details) {
    if ($null -eq $details) { return 'none' }
    $entries = New-Object System.Collections.Generic.List[string]
    foreach ($p in $details.PSObject.Properties) {
        if ($entries.Count -ge 12) { break }
        if ($p.Name -notmatch '^(poll|attempt|success|failure|fail|request|response|retry|backoff|empty|inflight|queued|completed|timeout)[a-zA-Z0-9_]*$') { continue }
        if ($p.Value -is [bool]) {
            $entries.Add("$($p.Name)=$($p.Value.ToString().ToLowerInvariant())")
        } elseif ($p.Value -is [int] -or $p.Value -is [long] -or $p.Value -is [double]) {
            $entries.Add("$($p.Name)=$($p.Value)")
        }
    }
    if ($entries.Count -eq 0) { return 'none' }
    return ($entries -join ',')
}
for ($i = 1; $i -le $Samples; $i++) {
    Start-Sleep -Seconds $IntervalSeconds
    try {
        $probe = Invoke-WebRequest -Uri "$base/readyz" -TimeoutSec 4 -SkipHttpErrorCheck -UseBasicParsing
        $ready = ($probe.StatusCode -eq 200)
        $plane = Invoke-RestMethod -Uri "$base/health/control-plane" -TimeoutSec 4
        $mcp = Invoke-RestMethod -Uri "$base/health/mcp" -TimeoutSec 4
        Write-Host ("TUNNEL_LOCAL_HEALTH: sample={0}/{1} ready={2} control_status={3} control_state={4} control_reason={5} control_counters={6} mcp_status={7} mcp_state={8} mcp_reason={9}" -f
            $i, $Samples, $ready.ToString().ToLowerInvariant(),
            (Safe-Enum $plane.status), (Safe-Enum $plane.state), (Safe-Enum $plane.reason_code),
            (Safe-Counters $plane.details), (Safe-Enum $mcp.status),
            (Safe-Enum $mcp.state), (Safe-Enum $mcp.reason_code))
    } catch {
        Write-Host ("TUNNEL_LOCAL_HEALTH: sample={0}/{1} endpoint_unavailable=true (body and exception redacted)" -f $i, $Samples)
    }
}
Write-Host 'TUNNEL_LOCAL_HEALTH_SAMPLING_COMPLETE: no credentials or raw health JSON disclosed.'
