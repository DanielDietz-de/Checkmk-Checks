#requires -Version 5.1
<#
.SYNOPSIS
    Install or update the least-privilege gMSA virtualization spool task.
.DESCRIPTION
    Validates the gMSA locally, writes only non-secret path configuration,
    grants the account read access to every runtime dependency and directory
    traversal required by the collector, grants modify access only to the
    Checkmk spool directory, verifies the resulting NTFS rights, and registers
    a non-elevated task. Every mutation honors PowerShell ShouldProcess so
    -WhatIf remains side-effect free.
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
    <#
    .SYNOPSIS
        Resolve an optional installer path to an explicit or canonical value.
    .DESCRIPTION
        Returns the caller-provided path when non-empty and otherwise returns the
        package default. Subsequent confinement checks validate the resolved path
        before files, ACLs, or scheduled-task settings are changed.
    #>
    param(
        [AllowEmptyString()] [string]$Candidate,
        [Parameter(Mandatory)] [string]$Fallback
    )

    if ([string]::IsNullOrWhiteSpace($Candidate)) { return $Fallback }
    return $Candidate
}

function Test-S2DHciPathUnderRoot {
    <#
    .SYNOPSIS
        Verify that an installer path remains strictly below a trusted root.
    .DESCRIPTION
        Normalizes both paths and checks a separator-bounded prefix using
        case-insensitive Windows semantics. The installer uses this before writing
        configuration, granting ACLs, or registering the scheduled task.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-S2DHciGmsaUsable {
    <#
    .SYNOPSIS
        Require a locally installed and usable group Managed Service Account.
    .DESCRIPTION
        Requires Test-ADServiceAccount, extracts the gMSA SAM account name, and
        fails task installation unless Windows confirms the account can be used on
        this host. No password is requested, retrieved, or stored.
    #>
    param([Parameter(Mandatory)] [string]$Identity)

    $command = Get-Command -Name 'Test-ADServiceAccount' -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw 'Test-ADServiceAccount is required to validate the gMSA before task registration.' }
    $sam = $Identity.Split('\')[-1]
    if (-not (Test-ADServiceAccount -Identity $sam -ErrorAction Stop)) { throw "gMSA '$Identity' is not installed or usable on this host." }
}

function Grant-S2DHciAcl {
    <#
    .SYNOPSIS
        Grant one scoped NTFS permission to the configured gMSA identity.
    .DESCRIPTION
        Uses icacls with replacement semantics for the named identity and checks
        the native exit code. The caller must gate this mutating helper through
        ShouldProcess. Any ACL application failure terminates installation before
        the scheduled task is registered.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Identity,
        [Parameter(Mandatory)] [string]$Permission
    )

    & icacls.exe $Path /grant:r "${Identity}:$Permission" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to grant $Permission on '$Path' to '$Identity'." }
}

function Assert-S2DHciAclPresent {
    <#
    .SYNOPSIS
        Verify that the configured gMSA has the required effective NTFS rights.
    .DESCRIPTION
        Resolves the configured identity to its SID, reads the target ACL, and
        requires at least one allow rule for that SID containing every requested
        FileSystemRights bit. This verifies rights rather than merely checking that
        the account name appears in command output.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Identity,
        [Parameter(Mandatory)] [System.Security.AccessControl.FileSystemRights]$RequiredRights
    )

    $targetSid = (New-Object System.Security.Principal.NTAccount($Identity)).Translate([System.Security.Principal.SecurityIdentifier])
    $acl = Get-Acl -LiteralPath $Path
    foreach ($rule in $acl.Access) {
        if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) { continue }
        try { $ruleSid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]) }
        catch { continue }
        if ($ruleSid.Value -ne $targetSid.Value) { continue }
        if (($rule.FileSystemRights -band $RequiredRights) -eq $RequiredRights) { return }
    }
    throw "ACL verification failed for '$Identity' on '$Path'; required rights: $RequiredRights."
}

$AgentRoot = [System.IO.Path]::GetFullPath($AgentRoot)
$binRoot = Join-Path $AgentRoot 'bin'
$configRoot = Join-Path $AgentRoot 'config'
$spoolRoot = Join-Path $AgentRoot 'spool'
$commonModulePath = Join-Path $binRoot 's2d_hci_common.psm1'
$collectorConfigPath = Join-Path $configRoot 's2d_hci.json'
$CollectorPath = Resolve-S2DHciDefaultPath -Candidate $CollectorPath -Fallback (Join-Path $binRoot 's2d_hci_virtualization.ps1')
$WrapperPath = Resolve-S2DHciDefaultPath -Candidate $WrapperPath -Fallback (Join-Path $binRoot 's2d_hci_virtualization_spool.ps1')
$ConfigPath = Resolve-S2DHciDefaultPath -Candidate $ConfigPath -Fallback (Join-Path $configRoot 's2d_hci_virtualization_spool.json')
$SpoolFile = Resolve-S2DHciDefaultPath -Candidate $SpoolFile -Fallback (Join-Path $spoolRoot '600_s2d_hci_virtualization.txt')

foreach ($path in @($CollectorPath, $WrapperPath, $ConfigPath, $SpoolFile, $commonModulePath, $collectorConfigPath)) {
    if (-not (Test-S2DHciPathUnderRoot -Path $path -Root $AgentRoot)) { throw "Path must remain below '$AgentRoot': $path" }
}
if (-not (Test-S2DHciPathUnderRoot -Path $CollectorPath -Root $binRoot)) { throw 'Collector must be deployed below the Checkmk bin directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $WrapperPath -Root $binRoot)) { throw 'Wrapper must be deployed below the Checkmk bin directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $SpoolFile -Root $spoolRoot)) { throw 'Spool file must remain below the Checkmk spool directory.' }

if ($DryRun) {
    [pscustomobject]@{ TaskName=$TaskName; ServiceAccount=$ServiceAccount; CollectorPath=$CollectorPath; WrapperPath=$WrapperPath; CommonModulePath=$commonModulePath; CollectorConfigPath=$collectorConfigPath; ConfigPath=$ConfigPath; SpoolFile=$SpoolFile; RunLevel='Limited' }
    return
}

Assert-S2DHciGmsaUsable -Identity $ServiceAccount
foreach ($directory in @($configRoot, $spoolRoot)) {
    if (-not (Test-Path -LiteralPath $directory -PathType Container) -and $PSCmdlet.ShouldProcess($directory, 'Create directory')) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
}
foreach ($file in @($CollectorPath, $WrapperPath, $commonModulePath, $collectorConfigPath)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required file not found: $file" }
}

$plannedConfig = [ordered]@{ collector_path=$CollectorPath; spool_file=$SpoolFile }
if ($PSCmdlet.ShouldProcess($ConfigPath, 'Write non-secret spool configuration')) {
    $plannedConfig | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8 -Force
}

# Explicit traversal is required when inheritance on the agent tree is hardened.
$aclTargets = @(
    [pscustomobject]@{ Path=$AgentRoot; Permission='(RX)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::ReadAndExecute },
    [pscustomobject]@{ Path=$binRoot; Permission='(RX)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::ReadAndExecute },
    [pscustomobject]@{ Path=$configRoot; Permission='(RX)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::ReadAndExecute },
    [pscustomobject]@{ Path=$CollectorPath; Permission='(RX)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::ReadAndExecute },
    [pscustomobject]@{ Path=$WrapperPath; Permission='(RX)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::ReadAndExecute },
    [pscustomobject]@{ Path=$commonModulePath; Permission='(RX)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::ReadAndExecute },
    [pscustomobject]@{ Path=$collectorConfigPath; Permission='(R)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::Read },
    [pscustomobject]@{ Path=$ConfigPath; Permission='(R)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::Read },
    [pscustomobject]@{ Path=$spoolRoot; Permission='(OI)(CI)(M)'; RequiredRights=[System.Security.AccessControl.FileSystemRights]::Modify }
)
foreach ($target in $aclTargets) {
    if ($PSCmdlet.ShouldProcess($target.Path, "Grant $($target.Permission) NTFS rights to $ServiceAccount")) {
        Grant-S2DHciAcl -Path $target.Path -Identity $ServiceAccount -Permission $target.Permission
        Assert-S2DHciAclPresent -Path $target.Path -Identity $ServiceAccount -RequiredRights $target.RequiredRights
    }
}

$taskArgument = "-NoProfile -NonInteractive -File `"$WrapperPath`" -ConfigPath `"$ConfigPath`" -AgentRoot `"$AgentRoot`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArgument
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$principal = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes ([Math]::Max(2, $IntervalMinutes - 1))) -StartWhenAvailable
if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task as $ServiceAccount")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
}

$status = if ($WhatIfPreference) { 'WhatIf' } else { 'InstalledOrUpdated' }
[pscustomobject]@{ TaskName=$TaskName; ServiceAccount=$ServiceAccount; Status=$status; RunLevel='Limited'; ConfigPath=$ConfigPath; SpoolFile=$SpoolFile }
