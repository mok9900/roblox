param([switch]$RequireRegistered)
$ErrorActionPreference = 'Stop'
# Credential-free check of the official Roblox Studio browser callback
# registration. Never execute the protocol, print handler command lines, or
# inspect URLs, cookies, credentials, account data or OAuth tokens.
$roots = @(
    'Registry::HKEY_CURRENT_USER\Software\Classes\roblox-studio-auth',
    'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Classes\roblox-studio-auth',
    'Registry::HKEY_CLASSES_ROOT\roblox-studio-auth'
)
$valid = $false
foreach ($path in $roots) {
    $exists = Test-Path -LiteralPath $path
    $protocol = $false
    $commandExists = $false
    $studioHandler = $false
    if ($exists) {
        try {
            $key = Get-Item -LiteralPath $path
            $protocol = $null -ne $key.GetValue('URL Protocol', $null)
        } catch {}
        $cmdPath = "$path\shell\open\command"
        $commandExists = Test-Path -LiteralPath $cmdPath
        if ($commandExists) {
            try {
                $cmd = [string](Get-Item -LiteralPath $cmdPath).GetValue('')
                $studioHandler = $cmd -match '(?i)RobloxStudioBeta(?:\.exe)?'
            } catch {}
        }
    }
    $root = if ($path -match 'CURRENT_USER') {'HKCU'} elseif ($path -match 'LOCAL_MACHINE') {'HKLM'} else {'HKCR'}
    Write-Host "STUDIO_AUTH_SCHEME_DIAG: root=$root registered=$exists url_protocol=$protocol command=$commandExists studio_handler=$studioHandler"
    if ($exists -and $protocol -and $commandExists -and $studioHandler) { $valid = $true }
}
if ($valid) {
    Write-Host 'STUDIO_AUTH_SCHEME_REGISTERED: Roblox Studio protocol handler has a valid-looking registration.'
} else {
    Write-Host 'STUDIO_AUTH_SCHEME_NOT_CONFIRMED: browser login may not hand off to Studio.'
    if ($RequireRegistered) { throw 'OFFICIAL_STUDIO_AUTH_SCHEME_UNREGISTERED' }
}
