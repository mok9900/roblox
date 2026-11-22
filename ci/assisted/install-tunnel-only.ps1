# Install ONLY the official OpenAI Secure MCP Tunnel Windows binary.
# No Roblox Studio login, no Gmail, no game editing.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'TUNNEL_ONLY_INSTALL_HOSTED_WINDOWS_REQUIRED'
}
$toolDir = Join-Path $env:RUNNER_TEMP 'openai-tunnel-only-probe'
New-Item -ItemType Directory -Path $toolDir -Force | Out-Null
$headers = @{ 'User-Agent'='roblox-ci-no-auth-tunnel-probe'; 'Accept'='application/vnd.github+json' }
if ($env:GH_TOKEN) { $headers['Authorization'] = "Bearer $env:GH_TOKEN" }
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/openai/tunnel-client/releases/latest' -Headers $headers -TimeoutSec 50
$target = @($release.assets | Where-Object { $_.name -match '^tunnel-client-v[0-9].*-windows-amd64[.]zip$' } | Select-Object -First 1)
$sums = @($release.assets | Where-Object { $_.name -eq 'SHA256SUMS.txt' } | Select-Object -First 1)
if ($target.Count -ne 1 -or $sums.Count -ne 1) {
    throw 'TUNNEL_OFFICIAL_RELEASE_ASSETS_MISSING'
}
$zip=Join-Path $toolDir 'tunnel-client.zip'
$sumFile=Join-Path $toolDir 'SHA256SUMS.txt'
Invoke-WebRequest -Uri $target[0].browser_download_url -OutFile $zip -TimeoutSec 120
Invoke-WebRequest -Uri $sums[0].browser_download_url -OutFile $sumFile -TimeoutSec 60
$line=@(Get-Content -LiteralPath $sumFile | Where-Object { $_ -match [regex]::Escape($target[0].name) + '$' } | Select-Object -First 1)
if ($line.Count -ne 1) { throw 'TUNNEL_OFFICIAL_CHECKSUM_NOT_LISTED' }
$expected=($line[0] -split '\s+')[0].ToLowerInvariant()
$actual=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected -ne $actual) { throw 'TUNNEL_OFFICIAL_RELEASE_CHECKSUM_MISMATCH' }
$dest=Join-Path $toolDir 'unpacked'
Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
$exe=@(Get-ChildItem -LiteralPath $dest -Recurse -File | Where-Object { $_.Name -eq 'tunnel-client.exe' } | Select-Object -First 1)
if ($exe.Count -ne 1) { throw 'TUNNEL_OFFICIAL_EXECUTABLE_MISSING' }
"TUNNEL_EXE=$($exe[0].FullName)" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
Write-Host 'TUNNEL_OFFICIAL_ONLY_INSTALLED_AND_SHA256_VERIFIED: no Roblox credentials used.'
