#requires -Version 5.1
<#
.SYNOPSIS
    Installs the S2D/HCI virtualization spool collector task for a gMSA.

.DESCRIPTION
    Creates or updates a Windows Scheduled Task that runs the packaged spool wrapper
    under a pre-authorized group Managed Service Account (gMSA). The script stores
    only non-secret paths and does not accept, retrieve, or persist a password.

    The task is deliberately restricted to a gMSA because ordinary service accounts
    require a separate, securely managed credential-registration process.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[^\\]+\\[^\\]+\$$')]
    [string]$ServiceAccount,

    [string]$TaskName = 'Checkmk S2D HCI Virtualization Collector',
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent'),

    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 5,

    [string]$CollectorPath,
    [string]$WrapperPath,
    [string]$ConfigPath,
    [string]$SpoolFile,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-DefaultPath {
    param(
        [Parameter(Mandatory)] [AllowEmptyString()] [string]$Candidate,
        [Parameter(Mandatory)] [string]$Fallback
    )
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return $Fallback }
    return $Candidate
}

function Test-PathUnderRoot {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

$AgentRoot = [System.IO.Path]::GetFullPath($AgentRoot)
$CollectorPath = Resolve-DefaultPath -Candidate $CollectorPath -Fallback (Join-Path $AgentRoot 'plugins\s2d_hci_virtualization.ps1')
$WrapperPath = Resolve-DefaultPath -Candidate $WrapperPath -Fallback (Join-Path $AgentRoot 'scripts\s2d_hci_virtualization_spool.ps1')
$ConfigPath = Resolve-DefaultPath -Candidate $ConfigPath -Fallback (Join-Path $AgentRoot 'config\s2d_hci_virtualization.json')
$SpoolFile = Resolve-DefaultPath -Candidate $SpoolFile -Fallback (Join-Path $AgentRoot 'spool\600_s2d_hci_virtualization.txt')

$spoolRoot = Join-Path $AgentRoot 'spool'
$configRoot = Join-Path $AgentRoot 'config'
$scriptRoot = Join-Path $AgentRoot 'scripts'

foreach ($pathToValidate in @($CollectorPath, $WrapperPath, $ConfigPath, $SpoolFile)) {
    if (-not (Test-PathUnderRoot -Path $pathToValidate -Root $AgentRoot)) {
        throw "Path must remain below Checkmk agent root '$AgentRoot': $pathToValidate"
    }
}
if (-not (Test-PathUnderRoot -Path $SpoolFile -Root $spoolRoot)) {
    throw "Spool file must remain below Checkmk spool root '$spoolRoot': $SpoolFile"
}

$plannedConfig = [ordered]@{
    collector_path = $CollectorPath
    spool_file = $SpoolFile
    require_paths_under_agent_root = $true
}
$taskArgument = "-NoProfile -NonInteractive -File `"$WrapperPath`" -ConfigPath `"$ConfigPath`" -AgentRoot `"$AgentRoot`""

if ($DryRun) {
    [pscustomobject]@{
        TaskName = $TaskName
        ServiceAccount = $ServiceAccount
        AgentRoot = $AgentRoot
        IntervalMinutes = $IntervalMinutes
        WrapperPath = $WrapperPath
        ConfigPath = $ConfigPath
        CollectorPath = $CollectorPath
        SpoolFile = $SpoolFile
        WouldWriteConfig = $true
        WouldRegisterTask = $true
    }
    return
}

foreach ($directory in @($spoolRoot, $configRoot, $scriptRoot)) {
    if (-not (Test-Path -LiteralPath $directory -PathType Container) -and $PSCmdlet.ShouldProcess($directory, 'Create directory')) {
        New-Item -Path $directory -ItemType Directory -Force | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $WrapperPath -PathType Leaf)) {
    throw "Wrapper script does not exist: $WrapperPath"
}
if (-not (Test-Path -LiteralPath $CollectorPath -PathType Leaf)) {
    throw "Collector script does not exist: $CollectorPath"
}

if ($PSCmdlet.ShouldProcess($ConfigPath, 'Write non-secret collector configuration')) {
    $plannedConfig | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8 -Force
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArgument
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$principal = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes ([Math]::Max(2, $IntervalMinutes - 1))) -StartWhenAvailable

if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task as $ServiceAccount")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
}

[pscustomobject]@{
    TaskName = $TaskName
    ServiceAccount = $ServiceAccount
    AgentRoot = $AgentRoot
    IntervalMinutes = $IntervalMinutes
    ConfigPath = $ConfigPath
    SpoolFile = $SpoolFile
    Status = 'InstalledOrUpdated'
}
