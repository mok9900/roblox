$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$reportDir = Join-Path $env:GITHUB_WORKSPACE 'studio-probe-output'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$reportFile = Join-Path $reportDir 'report.json'
$installer = Join-Path $env:RUNNER_TEMP 'RobloxStudioInstaller.exe'
$smokeFile = Join-Path $env:GITHUB_WORKSPACE 'ci\smoke.luau'
$smokeOutput = Join-Path $reportDir 'studio-script-output.log'
$state = [ordered]@{
    tested_utc = (Get-Date).ToUniversalTime().ToString('o')
    runner_os = $env:RUNNER_OS
    runner_image = $env:ImageOS
    runner_arch = $env:RUNNER_ARCH
    is_installed = $false
    process_launched = $false
    luau_executed = $false
    process_exit_code = $null
    installer_signature = $null
    error = $null
}
function Find-StudioExe {
    $programFilesX86 = [Environment]::GetFolderPath('ProgramFilesX86')
    $patterns = @(
        (Join-Path $env:LOCALAPPDATA 'Roblox\Versions\*\RobloxStudioBeta.exe'),
        (Join-Path $programFilesX86 'Roblox\Versions\*\RobloxStudioBeta.exe'),
        (Join-Path $env:ProgramFiles 'Roblox\Versions\*\RobloxStudioBeta.exe')
    )
    $found = @(Get-ChildItem -Path $patterns -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($found.Count -gt 0) { return $found[0] }
    return $null
}
try {
    Write-Host '=== RUNNER ENVIRONMENT ==='
    $cpu = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
    $os = Get-CimInstance Win32_OperatingSystem
    $video = @(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, VideoProcessor)
    $disk = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType = 3" | Select-Object DeviceID, FreeSpace, Size)
    $state.cpu = $cpu
    $state.ram_gb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $state.graphics = $video
    $state.disks = $disk
    $state.session_name = $env:SESSIONNAME
    Write-Host ($state | ConvertTo-Json -Depth 5)
    Write-Host '=== DOWNLOAD AND VERIFY OFFICIAL ROBLOX INSTALLER ==='
    Invoke-WebRequest -Uri 'https://setup.rbxcdn.com/RobloxStudioInstaller.exe' -OutFile $installer -UseBasicParsing -TimeoutSec 180
    $sig = Get-AuthenticodeSignature -FilePath $installer
    $state.installer_signature = @{ status = "$($sig.Status)"; signer = "$($sig.SignerCertificate.Subject)" }
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notlike '*O=Roblox Corporation*') {
        throw "Roblox installer signature validation failed: $($sig.Status), signer $($sig.SignerCertificate.Subject)"
    }
    Write-Host '=== START INSTALLER ==='
    $installerProc = Start-Process -FilePath $installer -PassThru
    $state.installer_pid = $installerProc.Id
    $deadline = (Get-Date).AddMinutes(7)
    $studio = $null
    while ((Get-Date) -lt $deadline) {
        $studio = Find-StudioExe
        if ($null -ne $studio) { break }
        Start-Sleep -Seconds 5
    }
    if ($null -eq $studio) { throw 'RobloxStudioBeta.exe not found after 7 minutes.' }
    $state.is_installed = $true
    $state.studio_path = $studio.FullName
    $state.mcp_launcher_present = Test-Path (Join-Path $env:LOCALAPPDATA 'Roblox\mcp.bat')
    Write-Host "Studio installed: $($studio.FullName)"
    Write-Host 'Close installer-started Studio so the CLI test starts its own process.'
    Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-Host '=== RUN OFFICIAL --task RunScript SMOKE TEST ==='
    if (-not (Test-Path $smokeFile)) { throw "Missing smoke script: $smokeFile" }
    $cmdArgs = '--task RunScript --runScriptFile "' + $smokeFile + '" --outputFile "' + $smokeOutput + '" --quitAfterExecution'
    $studioProc = Start-Process -FilePath $studio.FullName -ArgumentList $cmdArgs -PassThru
    $state.process_launched = $true
    $state.studio_pid = $studioProc.Id
    $deadline = (Get-Date).AddMinutes(4)
    while ((Get-Date) -lt $deadline) {
        $studioProc.Refresh()
        if ($studioProc.HasExited) { break }
        Start-Sleep -Seconds 3
    }
    $studioProc.Refresh()
    if ($studioProc.HasExited) {
        $state.process_exit_code = $studioProc.ExitCode
        Write-Host "Studio exit code: $($studioProc.ExitCode)"
    } else {
        Write-Warning 'Studio did not exit after 4 minutes; stopping it.'
        Stop-Process -Id $studioProc.Id -Force -ErrorAction SilentlyContinue
    }
    $output = ''
    if (Test-Path $smokeOutput) { $output = Get-Content -Path $smokeOutput -Raw -ErrorAction SilentlyContinue }
    if ($output) { Write-Host $output }
    $state.luau_executed = ($output -match 'GH_ACTIONS_STUDIO_RUNSCRIPT_OK')
    if (-not $state.luau_executed) { throw 'No Luau success marker found in the Studio CLI output file.' }
    Write-Host 'RESULT: STUDIO_LUAU_EXECUTION_CONFIRMED'
}
catch {
    $state.error = $_.Exception.Message
    Write-Warning "Studio probe failed: $($state.error)"
}
finally {
    try {
        $robloxLogDir = Join-Path $env:LOCALAPPDATA 'Roblox\logs'
        if (Test-Path $robloxLogDir) {
            Get-ChildItem $robloxLogDir -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 5 |
                ForEach-Object { Copy-Item $_.FullName (Join-Path $reportDir $_.Name) -ErrorAction SilentlyContinue }
        }
        $state | ConvertTo-Json -Depth 7 | Set-Content -Path $reportFile -Encoding utf8
        $summary = @(
            '## Roblox Studio Windows Actions probe'
            ''
            "- Installer detected: $($state.is_installed)"
            "- Studio process started: $($state.process_launched)"
            "- Studio successfully ran Luau script: $($state.luau_executed)"
            "- Error: $($state.error)"
            ''
            'See uploaded studio-probe-output artifact for report.json and Studio logs.'
        )
        $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Encoding utf8 -Append
        Write-Host '=== FINAL REPORT ==='
        Write-Host ($state | ConvertTo-Json -Depth 7)
    } catch { Write-Warning "Could not write final report: $($_.Exception.Message)" }
}
if (-not $state.luau_executed) { exit 1 }
exit 0
