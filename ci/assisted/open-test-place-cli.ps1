param([switch]$LaunchOnly, [switch]$DownloadOnly)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Pinned archived Roblox-owned test fixture, never uploaded to the user's games.
$fixtureCommit = '91182f4016e67a8d162fc41176a9ae3275463fd1'
$fixtureUrl = "https://raw.githubusercontent.com/Roblox/rbx-test-files/$fixtureCommit/places/baseplate-413/xml.rbxlx"
$placeDir = Join-Path $env:RUNNER_TEMP 'roblox-assisted\local-place'
New-Item -ItemType Directory -Force -Path $placeDir | Out-Null
$placeFile = Join-Path $placeDir 'CI_Only_Baseplate_Test.rbxlx'
Write-Host 'PLACE_FILE_DOWNLOAD: fetching archived Roblox Baseplate fixture by pinned commit.'
Invoke-WebRequest -Uri $fixtureUrl -OutFile $placeFile -TimeoutSec 120
$raw = [System.IO.File]::ReadAllText($placeFile)
if ($raw.Length -lt 1000 -or $raw -notmatch '<roblox ' -or $raw -notmatch 'version="4"' -or $raw -notmatch '<Item class="Workspace"') {
    throw 'PLACE_FILE_INVALID: Roblox fixture failed basic XML structure checks.'
}
[xml]$parsed = $raw
if ($parsed.roblox.version -ne '4') { throw 'PLACE_XML_VERSION_INVALID' }
Write-Host "PLACE_FILE_READY: downloaded; bytes=$((Get-Item $placeFile).Length)"
Write-Host "PLACE_FIXTURE_SHA256: $((Get-FileHash -Path $placeFile -Algorithm SHA256).Hash)"

if ($DownloadOnly) { Write-Host 'PLACE_DOWNLOAD_ONLY_OK'; return }
Write-Host 'PLACE_CLI_LAUNCH: issuing official --task EditFile with local test file.'
$launchArgs = '--task EditFile --localPlaceFile "' + $placeFile + '"'
$proc = Start-Process -FilePath $env:STUDIO_EXE -ArgumentList $launchArgs -PassThru
Write-Host 'PLACE_CLI_PROCESS_STARTED: EditFile task issued.'
if ($LaunchOnly) { Write-Host 'PLACE_CLI_LAUNCH_ONLY: not asserting editor login yet.'; return }
python .\ci\assisted\probe-editor-cli.py
if ($LASTEXITCODE -ne 0) {
    throw 'PLACE_EDITOR_NOT_VERIFIED: local EditFile task did not produce a confirmed open editor.'
}
"CI_TEST_PLACE_PATH=$placeFile" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
Write-Host 'PLACE_EDITOR_VERIFIED: local Baseplate opened; published games unchanged.'
