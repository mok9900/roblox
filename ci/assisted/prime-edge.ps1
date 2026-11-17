$ErrorActionPreference='Stop'
# Edge UIA page DOM accessibility may be disabled by default on unattended
# Windows Server hosts. Pre-open Edge with renderer accessibility enabled.
$edgePaths = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)
$edge = $edgePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $edge) { throw 'EDGE_EXE_NOT_FOUND' }
Start-Process -FilePath $edge -ArgumentList @('--no-first-run','--force-renderer-accessibility','--new-window','about:blank') | Out-Null
Start-Sleep -Seconds 4
Write-Host 'EDGE_ACCESSIBILITY_PRIMED: no credentials entered.'
