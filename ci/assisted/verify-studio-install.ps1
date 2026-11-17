param(
    [Parameter(Mandatory=$true)][string]$StudioPath,
    [int]$TimeoutSeconds = 420
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (-not (Test-Path -LiteralPath $StudioPath -PathType Leaf)) {
    throw 'STUDIO_INSTALL_VALIDATION_EXE_MISSING'
}
$root = Split-Path -Parent $StudioPath
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$previous = ''
$stable = 0
$lastLog = [datetime]::MinValue

# The installer writes RobloxStudioBeta.exe before extracting all of the
# bundled content/engine assets. File presence alone is NOT install completion.
while ((Get-Date) -lt $deadline) {
    $hasContent = Test-Path -LiteralPath (Join-Path $root 'content') -PathType Container
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue)
    $count = $files.Count
    $bytes = [long](($files | Measure-Object -Property Length -Sum).Sum)
    $installers = @(Get-Process -Name 'RobloxStudioInstaller*' -ErrorAction SilentlyContinue)
    # Use only aggregate metadata, never dump paths, files, logs or accounts.
    $looksComplete = $hasContent -and $count -ge 200 -and $bytes -ge 150MB -and $installers.Count -eq 0
    $sig = "$count/$bytes"
    if ($looksComplete -and $sig -eq $previous) {
        $stable++
    } elseif ($looksComplete) {
        $stable = 1
    } else {
        $stable = 0
    }
    $previous = $sig

    if (((Get-Date) - $lastLog).TotalSeconds -ge 20) {
        Write-Host ("STUDIO_INSTALL_PROGRESS: content={0}, files={1}, size_mb={2}, installers={3}, stable={4}" -f $hasContent, $count, [math]::Round($bytes / 1MB), $installers.Count, $stable)
        $lastLog = Get-Date
    }
    if ($stable -ge 3) {
        Write-Host ("STUDIO_INSTALL_VERIFIED: content=True, files={0}, size_mb={1}, installer_processes=0, stable_checks={2}" -f $count, [math]::Round($bytes / 1MB), $stable)
        exit 0
    }
    Start-Sleep -Seconds 6
}
throw 'STUDIO_INSTALL_INCOMPLETE: file tree did not stabilize with content, expected assets and terminated installer'
