$ErrorActionPreference = 'Stop'
# Microsoft's documented supported policy:
# https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies/hidefirstrunexperience
# Applies only to the transient GitHub runner's current user profile.
$policy = 'HKCU:\SOFTWARE\Policies\Microsoft\Edge'
New-Item -Path $policy -Force | Out-Null
New-ItemProperty -Path $policy -Name 'HideFirstRunExperience' -PropertyType DWord -Value 1 -Force | Out-Null
$actual = (Get-ItemProperty -Path $policy -Name 'HideFirstRunExperience').HideFirstRunExperience
if ($actual -ne 1) { throw 'EDGE_FIRST_RUN_POLICY_NOT_APPLIED' }
Write-Host 'EDGE_FIRST_RUN_DISABLED: official Microsoft policy applied to the disposable Actions runner.'

# Microsoft Edge official AutoLaunchProtocolsFromOrigins policy.
# Browser OAuth can return through the registered "roblox-studio-auth"
# Windows URL handler. On disposable CI runners, explicitly permit ONLY
# that protocol from Roblox-owned HTTPS origins. Never use "*" here and
# never modify the user's own device or launch any callback URI ourselves.
# Reference: https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies/autolaunchprotocolsfromorigins
$trustedOrigins = @(
    'https://www.roblox.com',
    'https://apis.roblox.com',
    'https://create.roblox.com'
)
$entry = @(@{
    protocol = 'roblox-studio-auth'
    allowed_origins = $trustedOrigins
})
$json = ConvertTo-Json -InputObject $entry -Depth 4 -Compress
New-ItemProperty -Path $policy -Name 'AutoLaunchProtocolsFromOrigins' -PropertyType String -Value $json -Force | Out-Null
$check = [string](Get-ItemProperty -Path $policy -Name 'AutoLaunchProtocolsFromOrigins').AutoLaunchProtocolsFromOrigins
$parsed = @($check | ConvertFrom-Json)
if ($parsed.Count -ne 1 -or $parsed[0].protocol -ne 'roblox-studio-auth' -or
    @($parsed[0].allowed_origins).Count -ne $trustedOrigins.Count -or
    @($parsed[0].allowed_origins | Where-Object { $_ -notin $trustedOrigins }).Count -gt 0) {
    throw 'EDGE_ROBLOX_PROTOCOL_ALLOWLIST_INVALID'
}
Write-Host "EDGE_ROBLOX_AUTH_PROTOCOL_ALLOWLIST_READY: protocol=roblox-studio-auth origins=$($trustedOrigins.Count) scope=transient_current_user"
