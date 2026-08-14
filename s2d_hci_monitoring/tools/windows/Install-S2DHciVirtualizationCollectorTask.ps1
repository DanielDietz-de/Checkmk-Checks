#requires -Version 5.1
<#
.SYNOPSIS
    Install or update the least-privilege gMSA virtualization spool task.
.DESCRIPTION
    Validates the gMSA locally, derives a spool lifetime that safely covers the
    configured task interval, recovers the configuration path registered on an
    existing task, quiesces any existing publisher before generated-state changes,
    retires any previously configured spool snapshot when its path changes, writes
    only non-secret path configuration, grants the account read access to every
    runtime dependency and directory traversal required by the collector, grants
    modify access only to the Checkmk spool directory, verifies the resulting NTFS
    rights, and registers a non-elevated task. Every mutation honors PowerShell
    ShouldProcess so -WhatIf remains side-effect free.
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

function Get-S2DHciSpoolLifetimeSeconds {
    <#
    .SYNOPSIS
        Derive the Checkmk spool lifetime from the scheduled collection interval.
    .DESCRIPTION
        Keeps the historical ten-minute minimum and otherwise retains spool data
        for two full intervals. This prevents normal data from aging out before the
        next collection and tolerates one missed or delayed run.
    #>
    param([Parameter(Mandatory)] [ValidateRange(1, 1440)] [int]$IntervalMinutes)

    [int64]$intervalSeconds = [int64]$IntervalMinutes * 60
    [int64]$lifetimeSeconds = [Math]::Max([int64]600, $intervalSeconds * 2)
    return [int]$lifetimeSeconds
}

function Assert-S2DHciSpoolLifetime {
    <#
    .SYNOPSIS
        Validate the numeric Checkmk spool prefix against the scheduled interval.
    .DESCRIPTION
        Requires a leading `<seconds>_` filename prefix and a lifetime of at least
        two collection intervals. Custom spool paths therefore cannot silently
        create monitoring gaps by expiring before the scheduled task runs again.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [ValidateRange(1, 1440)] [int]$IntervalMinutes
    )

    $name = [System.IO.Path]::GetFileName($Path)
    if ($name -notmatch '^(\d+)_') {
        throw "Spool file '$name' must begin with a numeric Checkmk lifetime prefix such as '600_'."
    }
    [int64]$lifetimeSeconds = 0
    if (-not [int64]::TryParse($Matches[1], [ref]$lifetimeSeconds)) {
        throw "Spool lifetime prefix is not a valid integer: $name"
    }
    [int64]$minimumSeconds = [int64]$IntervalMinutes * 120
    if ($lifetimeSeconds -lt $minimumSeconds) {
        throw "Spool lifetime $lifetimeSeconds seconds is shorter than the required two task intervals ($minimumSeconds seconds)."
    }
    return [int]$lifetimeSeconds
}

function Test-S2DHciPathUnderRoot {
    <#
    .SYNOPSIS
        Verify that an installer path remains strictly below a trusted root.
    .DESCRIPTION
        Normalizes both paths and checks a separator-bounded prefix using
        case-insensitive Windows semantics. The installer uses this before writing
        configuration, removing old state, granting ACLs, or registering the task.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-S2DHciRegisteredConfigPath {
    <#
    .SYNOPSIS
        Recover the spool configuration path from the existing scheduled task.
    .DESCRIPTION
        Reads the root Task Scheduler entry with the configured task name and
        enumerates every -ConfigPath argument across all registered actions. The
        task is accepted only when exactly one argument is present. The recovered
        path is canonicalized and confined to the trusted Checkmk config directory.
        Missing, duplicate, ambiguous, or untrusted state is rejected rather than
        overwritten blindly.
    #>
    param(
        [Parameter(Mandatory)] [string]$TaskName,
        [Parameter(Mandatory)] [string]$ConfigRoot
    )

    $existingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction SilentlyContinue
    if ($null -eq $existingTask) { return $null }
    if (@($existingTask).Count -ne 1) {
        throw "Expected exactly one root scheduled task named '$TaskName'; remove ambiguous task state before reinstalling."
    }

    $configPaths = [System.Collections.Generic.List[string]]::new()
    foreach ($taskAction in @($existingTask.Actions)) {
        $arguments = [string]$taskAction.Arguments
        if ([string]::IsNullOrWhiteSpace($arguments)) { continue }
        $argumentMatches = [regex]::Matches($arguments, '(?i)(?:^|\s)-ConfigPath\s+(?:"([^"]+)"|''([^'']+)''|(\S+))')
        foreach ($match in $argumentMatches) {
            $captured = @($match.Groups[1].Value, $match.Groups[2].Value, $match.Groups[3].Value) |
                Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
                Select-Object -First 1
            if (-not [string]::IsNullOrWhiteSpace([string]$captured)) {
                $configPaths.Add([System.IO.Path]::GetFullPath([string]$captured))
            }
        }
    }

    if ($configPaths.Count -ne 1) {
        throw "Existing scheduled task '$TaskName' does not expose exactly one recoverable -ConfigPath; remove and reinstall it explicitly."
    }
    $registered = $configPaths[0]
    if (-not (Test-S2DHciPathUnderRoot -Path $registered -Root $ConfigRoot)) {
        throw "Existing scheduled task '$TaskName' references a configuration path outside the trusted config directory: $registered"
    }
    return $registered
}

function Stop-S2DHciScheduledTaskPublisher {
    <#
    .SYNOPSIS
        Quiesce an existing scheduled collector before changing generated state.
    .DESCRIPTION
        Disables the root task first so no new trigger can start, immediately stops
        all running task instances, and then verifies that the task is no longer in
        the Running state within a bounded timeout. The task remains disabled if a
        later update step fails, which is intentionally fail-closed: an old
        publisher cannot recreate a retired spool snapshot after cleanup.
    #>
    param(
        [Parameter(Mandatory)] [string]$TaskName,
        [ValidateRange(1, 120)] [int]$TimeoutSeconds = 30
    )

    $existingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop
    if (@($existingTask).Count -ne 1) {
        throw "Expected exactly one root scheduled task named '$TaskName' while quiescing the collector."
    }

    Disable-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop | Out-Null
    Stop-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop | Out-Null

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $currentTask = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop
        if (@($currentTask).Count -ne 1) {
            throw "Scheduled task '$TaskName' became ambiguous while waiting for it to stop."
        }
        if ([string]$currentTask.State -ne 'Running') { return }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)

    throw "Scheduled task '$TaskName' did not stop within $TimeoutSeconds seconds; generated state was not changed."
}

function Read-S2DHciPreviousSpoolFile {
    <#
    .SYNOPSIS
        Read the previously configured spool path before updating configuration.
    .DESCRIPTION
        Loads the existing non-secret spool configuration, requires a non-empty
        spool_file field, normalizes it, and rejects any path outside the trusted
        Checkmk spool directory. Invalid existing state stops the update rather
        than risking deletion of an arbitrary path or leaving an unknown snapshot.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$SpoolRoot
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try { $existing = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop }
    catch { throw "Existing spool configuration is invalid; refusing update until it is repaired or removed: $Path" }
    if (-not ($existing.PSObject.Properties.Name -contains 'spool_file') -or [string]::IsNullOrWhiteSpace([string]$existing.spool_file)) {
        throw "Existing spool configuration has no valid spool_file; refusing update: $Path"
    }
    $previous = [System.IO.Path]::GetFullPath([string]$existing.spool_file)
    if (-not (Test-S2DHciPathUnderRoot -Path $previous -Root $SpoolRoot)) {
        throw "Existing spool configuration points outside the trusted spool directory: $previous"
    }
    return $previous
}

function Remove-S2DHciGeneratedFileIfPresent {
    <#
    .SYNOPSIS
        Remove one known package-generated file when it is present.
    .DESCRIPTION
        Performs an idempotent literal-path deletion. The caller supplies only a
        previously validated package-owned path and gates the mutation through
        ShouldProcess.
    #>
    param([Parameter(Mandatory)] [string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) { Remove-Item -LiteralPath $Path -Force }
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
        Verify that the configured gMSA has the required NTFS allow rights.
    .DESCRIPTION
        Resolves the configured identity to its SID, reads the target ACL, and
        requires at least one allow rule for that SID containing every requested
        FileSystemRights bit. This verifies the explicit rights installed by this
        tool rather than merely checking that the account name appears in output.
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
$spoolLifetimeSeconds = Get-S2DHciSpoolLifetimeSeconds -IntervalMinutes $IntervalMinutes
$CollectorPath = Resolve-S2DHciDefaultPath -Candidate $CollectorPath -Fallback (Join-Path $binRoot 's2d_hci_virtualization.ps1')
$WrapperPath = Resolve-S2DHciDefaultPath -Candidate $WrapperPath -Fallback (Join-Path $binRoot 's2d_hci_virtualization_spool.ps1')
$ConfigPath = Resolve-S2DHciDefaultPath -Candidate $ConfigPath -Fallback (Join-Path $configRoot 's2d_hci_virtualization_spool.json')
$SpoolFile = Resolve-S2DHciDefaultPath -Candidate $SpoolFile -Fallback (Join-Path $spoolRoot ("{0}_s2d_hci_virtualization.txt" -f $spoolLifetimeSeconds))
$CollectorPath = [System.IO.Path]::GetFullPath($CollectorPath)
$WrapperPath = [System.IO.Path]::GetFullPath($WrapperPath)
$ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
$SpoolFile = [System.IO.Path]::GetFullPath($SpoolFile)

foreach ($path in @($CollectorPath, $WrapperPath, $ConfigPath, $SpoolFile, $commonModulePath, $collectorConfigPath)) {
    if (-not (Test-S2DHciPathUnderRoot -Path $path -Root $AgentRoot)) { throw "Path must remain below '$AgentRoot': $path" }
}
if (-not (Test-S2DHciPathUnderRoot -Path $CollectorPath -Root $binRoot)) { throw 'Collector must be deployed below the Checkmk bin directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $WrapperPath -Root $binRoot)) { throw 'Wrapper must be deployed below the Checkmk bin directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $ConfigPath -Root $configRoot)) { throw 'Spool configuration must be deployed below the Checkmk config directory.' }
if (-not (Test-S2DHciPathUnderRoot -Path $SpoolFile -Root $spoolRoot)) { throw 'Spool file must remain below the Checkmk spool directory.' }
$spoolLifetimeSeconds = Assert-S2DHciSpoolLifetime -Path $SpoolFile -IntervalMinutes $IntervalMinutes
$registeredConfigPath = Get-S2DHciRegisteredConfigPath -TaskName $TaskName -ConfigRoot $configRoot
if ($null -ne $registeredConfigPath) {
    if (-not $registeredConfigPath.Equals($ConfigPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Existing scheduled task '$TaskName' uses ConfigPath '$registeredConfigPath'. Remove the task and generated state before reinstalling with '$ConfigPath'."
    }
    if (-not (Test-Path -LiteralPath $registeredConfigPath -PathType Leaf)) {
        throw "Existing scheduled task '$TaskName' references missing configuration '$registeredConfigPath'; remove and reinstall it before continuing."
    }
}
$previousConfigPath = if ($null -ne $registeredConfigPath) { $registeredConfigPath } else { $ConfigPath }
$previousSpoolFile = Read-S2DHciPreviousSpoolFile -Path $previousConfigPath -SpoolRoot $spoolRoot

if ($DryRun) {
    [pscustomobject]@{
        TaskName=$TaskName
        ServiceAccount=$ServiceAccount
        CollectorPath=$CollectorPath
        WrapperPath=$WrapperPath
        CommonModulePath=$commonModulePath
        CollectorConfigPath=$collectorConfigPath
        ConfigPath=$ConfigPath
        RegisteredConfigPath=$registeredConfigPath
        SpoolFile=$SpoolFile
        PreviousSpoolFile=$previousSpoolFile
        SpoolLifetimeSeconds=$spoolLifetimeSeconds
        RunLevel='Limited'
    }
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

if ($null -ne $registeredConfigPath) {
    if ($PSCmdlet.ShouldProcess($TaskName, 'Quiesce existing scheduled collector before generated-state update')) {
        Stop-S2DHciScheduledTaskPublisher -TaskName $TaskName
    }
}

if ($null -ne $previousSpoolFile -and -not $previousSpoolFile.Equals($SpoolFile, [System.StringComparison]::OrdinalIgnoreCase)) {
    if ($PSCmdlet.ShouldProcess($previousSpoolFile, 'Retire previously configured virtualization spool snapshot')) {
        Remove-S2DHciGeneratedFileIfPresent -Path $previousSpoolFile
    }
    if ($PSCmdlet.ShouldProcess($SpoolFile, 'Remove stale target virtualization spool snapshot before reconfiguration')) {
        Remove-S2DHciGeneratedFileIfPresent -Path $SpoolFile
    }
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
    Register-ScheduledTask -TaskName $TaskName -TaskPath '\' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    Enable-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop | Out-Null
}

$status = if ($WhatIfPreference) { 'WhatIf' } else { 'InstalledOrUpdated' }
[pscustomobject]@{
    TaskName=$TaskName
    ServiceAccount=$ServiceAccount
    Status=$status
    RunLevel='Limited'
    ConfigPath=$ConfigPath
    RegisteredConfigPath=$registeredConfigPath
    SpoolFile=$SpoolFile
    PreviousSpoolFile=$previousSpoolFile
    SpoolLifetimeSeconds=$spoolLifetimeSeconds
}
