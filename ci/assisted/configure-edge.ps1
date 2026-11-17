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
