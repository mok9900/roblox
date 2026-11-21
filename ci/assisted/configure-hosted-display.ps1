# Expand the disposable GitHub-hosted Windows interactive display.
# This is neither a self-hosted runner nor a virtual monitor driver install.
# If GitHub's current VM image does not support this mode, stay at the
# actual native resolution and let guarded Studio discovery fail closed.
$ErrorActionPreference = 'Stop'

$native = @'
using System;
using System.Runtime.InteropServices;
public static class CiScreenInfo {
  [DllImport("user32.dll", SetLastError=true)] public static extern int GetSystemMetrics(int nIndex);
}
'@
Add-Type -TypeDefinition $native -ErrorAction Stop
$beforeW = [CiScreenInfo]::GetSystemMetrics(0)
$beforeH = [CiScreenInfo]::GetSystemMetrics(1)
Write-Host "HOSTED_DISPLAY_BEFORE: width=$beforeW height=$beforeH"

if ($beforeW -ge 1600 -and $beforeH -ge 900) {
    Write-Host 'HOSTED_DISPLAY_READY: existing display already sufficient.'
    exit 0
}
$displayCmd = Get-Command Set-DisplayResolution -ErrorAction SilentlyContinue
if ($displayCmd) {
    try {
        Set-DisplayResolution -Width 1920 -Height 1080 -Force -ErrorAction Stop | Out-Null
        Write-Host 'HOSTED_DISPLAY_REQUEST: native Windows 1920x1080 requested.'
    } catch {
        # Avoid disclosing any localized or hardware-dependent Win32 strings.
        Write-Host 'HOSTED_DISPLAY_REQUEST: native API unavailable; retaining original mode.'
    }
} else {
    Write-Host 'HOSTED_DISPLAY_REQUEST: Set-DisplayResolution cmdlet absent.'
}
Start-Sleep -Seconds 2
$afterW = [CiScreenInfo]::GetSystemMetrics(0)
$afterH = [CiScreenInfo]::GetSystemMetrics(1)
Write-Host "HOSTED_DISPLAY_AFTER: width=$afterW height=$afterH"
if ($afterW -ge 1600 -and $afterH -ge 900) {
    Write-Host 'HOSTED_DISPLAY_EXPANDED: Studio full-width mezzanine can be tested.'
} else {
    Write-Host 'HOSTED_DISPLAY_FIXED_LOW_RES: retaining guarded, no-blind-click OCR fallback.'
}
