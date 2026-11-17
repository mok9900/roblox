$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$toolDir = Join-Path $env:RUNNER_TEMP 'roblox-assisted'
New-Item -ItemType Directory -Force -Path $toolDir | Out-Null

function Get-StudioExe {
    $paths = @(
        (Join-Path $env:ProgramFiles 'Roblox\Versions\*\RobloxStudioBeta.exe'),
        (Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Roblox\Versions\*\RobloxStudioBeta.exe'),
        (Join-Path $env:LOCALAPPDATA 'Roblox\Versions\*\RobloxStudioBeta.exe')
    )
    @(Get-ChildItem -Path $paths -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1) |
        Select-Object -First 1
}

Write-Host '[1/2] Installing signed Roblox Studio from Roblox CDN'
$installer = Join-Path $toolDir 'RobloxStudioInstaller.exe'
Invoke-WebRequest -Uri 'https://setup.rbxcdn.com/RobloxStudioInstaller.exe' -OutFile $installer -TimeoutSec 180
$signature = Get-AuthenticodeSignature $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Roblox Corporation') {
    throw 'Roblox installer signature is invalid or is not Roblox Corporation.'
}
$existing = Get-StudioExe
if (-not $existing) {
    Start-Process -FilePath $installer | Out-Null
    $deadline = (Get-Date).AddMinutes(5)
    while (-not $existing -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        $existing = Get-StudioExe
    }
}
if (-not $existing) { throw 'Roblox Studio executable not detected after installation.' }
$envFile = $env:GITHUB_ENV
"STUDIO_EXE=$($existing.FullName)" | Out-File -FilePath $envFile -Encoding utf8 -Append
Write-Host 'Roblox Studio executable found. (Path saved to GITHUB_ENV)'
Write-Host '[2/2] Downloading signed-release-checksum-verified OpenAI tunnel-client'
$gitHeaders = @{ 'User-Agent' = 'roblox-studio-actions'; 'Accept' = 'application/vnd.github+json' }
if ($env:GH_TOKEN) { $gitHeaders['Authorization'] = "Bearer $env:GH_TOKEN" }
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/openai/tunnel-client/releases/latest' -Headers $gitHeaders
$arch = [Environment]::Is64BitOperatingSystem
if (-not $arch) { throw 'This runner must be x64.' }
$target = @($release.assets | Where-Object { $_.name -match '^tunnel-client-v[0-9].*-windows-amd64[.]zip$' } | Select-Object -First 1)
$checksumAsset = @($release.assets | Where-Object { $_.name -eq 'SHA256SUMS.txt' } | Select-Object -First 1)
if (-not $target -or -not $checksumAsset) { throw 'Official OpenAI Windows AMD64 tunnel-client release asset not found.' }
$zip = Join-Path $toolDir 'tunnel-client.zip'
$sums = Join-Path $toolDir 'SHA256SUMS.txt'
Invoke-WebRequest -Uri $target[0].browser_download_url -OutFile $zip -TimeoutSec 180
Invoke-WebRequest -Uri $checksumAsset[0].browser_download_url -OutFile $sums -TimeoutSec 60
$sumLines = Get-Content $sums
$sumLine = @($sumLines | Where-Object { $_ -match [regex]::Escape($target[0].name) + '$' } | Select-Object -First 1)
if (-not $sumLine) { throw 'Tunnel download missing from official release SHA256SUMS manifest.' }
$expectedSha = ($sumLine[0] -split '\s+')[0].ToLowerInvariant()
$actualSha = (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha -ne $expectedSha) { throw 'OpenAI tunnel-client SHA256 mismatch.' }
$unpack = Join-Path $toolDir 'tunnel-client'
Expand-Archive -Path $zip -DestinationPath $unpack -Force
$exe = @(Get-ChildItem -Path $unpack -Filter 'tunnel-client.exe' -Recurse -File | Select-Object -First 1)
if (-not $exe) { throw 'OpenAI tunnel-client.exe not found inside official release ZIP.' }
"TUNNEL_EXE=$($exe[0].FullName)" | Out-File -FilePath $envFile -Encoding utf8 -Append
Write-Host 'OpenAI tunnel-client downloaded and SHA256 verified.'
& $exe[0].FullName --version
Write-Host 'Preflight complete. Authentication and MCP connectivity have NOT been verified.'
