#requires -Version 5.1
<#
.SYNOPSIS
    Install or update the least-privilege gMSA virtualization spool task.
.DESCRIPTION
    Validates the gMSA locally, writes only non-secret path configuration,
    grants the account read access to collector/config files and modify access
    only to the Checkmk spool directory, and registers a non-elevated task.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[^\\]+\\[^\\]+\$$')]
    [string]$ServiceAccount,
    [string]$TaskName = 'Checkmk S2D HCI Virtualization Collector',
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent'),
    [ValidateRange(1, 1440)] [int]$IntervalMinutes = 5,
    [string]$CollectorPath,
    [string]$WrapperPath,
    [string]$ConfigPath,
    [string]$SpoolFile,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-S2DHciDefaultPath {
    <# Return an explicit path or its canonical fallback when omitted. #>
    param(
        [AllowEmptyString()] [string]$Candidate,
        [Parameter(Mandatory)] [string]$Fallback
    )

    if ([string]::IsNullOrWhiteSpace($Candidate)) { return $Fallback }
    return $Candidate
}

function Test-S2DHciPathUnderRoot {
    <# Return true only when a normalized path remains below a trusted root. #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-S2DHciGmsaUsable {
    <# Require the ActiveDirectory validation cmdlet and a locally usable gMSA. #>
    param([Parameter(Mandatory)] [string]$Identity)

    $command = Get-Command -Name 'Test-ADServiceAccount' -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw 'Test-ADServiceAccount is required to validate the gMSA before task registration.' }
    $sam = $Identity.Split('\')[-1]
    if (-not (Test-ADServiceAccount -Identity $sam -ErrorAction Stop)) { throw "gMSA '$Identity' is not installed or usable on this host." }
}

function Grant-S2DHciAcl {
    <# Grant one explicit NTFS permission and fail when icacls cannot apply it. #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Identity,
        [Parameter(Mandatory)] [string]$Permission
    )

    & icacls.exe $Path /grant:r "${Identity}:$Permission" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to grant $Permission on '$Path' to '$Identity'." }
}

function Assert-S2DHciAclPresent {
    <# Verify that the resulting ACL text contains the configured gMSA identity. #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Identity
    )

    $output = (& icacls.exe $Path 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or $output.IndexOf($Identity, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "ACL verification failed for '$Identity' on '$Path'."
    }
}

$AgentRoot = [System.IO.Path]::GetFullPath($AgentRoot)
$binRoot = Join-Path $AgentRoot 'bin'
$configRoot = Join-Path $AgentRoot 'config'
$spoolRoot = Join-Path $AgentRoot 'spool'
$CollectorPath = Resolve-S2DHciDefaultPath -Candidate $CollectorPath -Fallback (Join-Path $binRoot 's2d_hci_virtualization.ps1')
$WrapperPath = Resolve-S2DHciDefaultPath -Candidate $WrapperPath -Fallback (Join-Path $binRoot 's2d_hci_virtualization_spool.ps1')
$ConfigPath = Resolve-S2DHciDefaultPath -Candidate $ConfigPath -Fallback (Join-Path $configRoot 's2d_hci_virtualization_spool.json')
$SpoolFile = Resolve-S2DHciDefaultPath -Candidate $SpoolFile -Fallback (Join-Path $spoolRoot '600_s2d_hci_virtualization.txt')

foreach ($path in @($CollectorPath, $WrapperPath, $ConfigPath, $SpoolFile)) {
    if (-not (Test-S2DHciPathUnderRoot -Path $path -Root $AgentRoot)) { throw "Path must remain below '$AgentRoot': $path" }
}
if (-not (Test-S2DHciPathUnderRoot -Path $CollectorPath -Root $binRoot)) { throw 'Collector must be deployed below the Checkmk bin directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $WrapperPath -Root $binRoot)) { throw 'Wrapper must be deployed below the Checkmk bin directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $SpoolFile -Root $spoolRoot)) { throw 'Spool file must remain below the Checkmk spool directory.' }

if ($DryRun) {
    [pscustomobject]@{ TaskName=$TaskName; ServiceAccount=$ServiceAccount; CollectorPath=$CollectorPath; WrapperPath=$WrapperPath; ConfigPath=$ConfigPath; SpoolFile=$SpoolFile; RunLevel='Limited' }
    return
}

Assert-S2DHciGmsaUsable -Identity $ServiceAccount
foreach ($directory in @($configRoot, $spoolRoot)) {
    if (-not (Test-Path -LiteralPath $directory -PathType Container) -and $PSCmdlet.ShouldProcess($directory, 'Create directory')) { New-Item -ItemType Directory -Path $directory -Force | Out-Null }
}
foreach ($file in @($CollectorPath, $WrapperPath)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required file not found: $file" }
}

$plannedConfig = [ordered]@{ collector_path=$CollectorPath; spool_file=$SpoolFile }
if ($PSCmdlet.ShouldProcess($ConfigPath, 'Write non-secret spool configuration')) {
    $plannedConfig | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8 -Force
}

Grant-S2DHciAcl -Path $CollectorPath -Identity $ServiceAccount -Permission '(RX)'
Grant-S2DHciAcl -Path $WrapperPath -Identity $ServiceAccount -Permission '(RX)'
Grant-S2DHciAcl -Path $ConfigPath -Identity $ServiceAccount -Permission '(R)'
Grant-S2DHciAcl -Path $spoolRoot -Identity $ServiceAccount -Permission '(OI)(CI)(M)'
foreach ($path in @($CollectorPath, $WrapperPath, $ConfigPath, $spoolRoot)) { Assert-S2DHciAclPresent -Path $path -Identity $ServiceAccount }

$taskArgument = "-NoProfile -NonInteractive -File `"$WrapperPath`" -ConfigPath `"$ConfigPath`" -AgentRoot `"$AgentRoot`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArgument
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$principal = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes ([Math]::Max(2, $IntervalMinutes - 1))) -StartWhenAvailable
if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task as $ServiceAccount")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
}

[pscustomobject]@{ TaskName=$TaskName; ServiceAccount=$ServiceAccount; Status='InstalledOrUpdated'; RunLevel='Limited'; ConfigPath=$ConfigPath; SpoolFile=$SpoolFile }
