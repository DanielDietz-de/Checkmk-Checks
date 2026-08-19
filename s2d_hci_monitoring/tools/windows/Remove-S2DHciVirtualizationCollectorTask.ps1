#requires -Version 5.1
<#
.SYNOPSIS
    Remove the S2D/HCI gMSA scheduled task and optional generated state.
.DESCRIPTION
    Recovers and validates generated state while the task still exists, quiesces
    the existing publisher by preventing new triggers and stopping all running
    instances, unregisters only the named root task, and, when explicitly
    requested, removes only validated generated spool/configuration state.
    Packaged collector files are left to the Checkmk agent package lifecycle.
    Every mutation honors ShouldProcess.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = 'Checkmk S2D HCI Virtualization Collector',
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent'),
    [string]$ConfigPath,
    [switch]$RemoveGeneratedState
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Handle test-s2dhcipathunderroot for this module's workflow.
function Test-S2DHciPathUnderRoot {
    <#
    .SYNOPSIS
        Verify that a generated-state path remains below the expected root.
    .DESCRIPTION
        Normalizes both paths and applies a separator-bounded, case-insensitive
        prefix check before any configured path is accepted for deletion.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

# Handle get-s2dhciregisteredconfigpath for this module's workflow.
function Get-S2DHciRegisteredConfigPath {
    <#
    .SYNOPSIS
        Recover the spool configuration path from the existing root task.
    .DESCRIPTION
        Reads the named root scheduled task and enumerates every -ConfigPath
        argument across all actions. Exactly one occurrence is required. The path
        is canonicalized and confined to the trusted Checkmk config directory so
        generated-state removal never follows ambiguous or untrusted task state.
    #>
    param(
        [Parameter(Mandatory)] [string]$TaskName,
        [Parameter(Mandatory)] [string]$ConfigRoot
    )

    $existingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction SilentlyContinue
    if ($null -eq $existingTask) { return $null }
    if (@($existingTask).Count -ne 1) {
        throw "Expected exactly one root scheduled task named '$TaskName'; inspect ambiguous task state before removal."
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
        throw "Existing scheduled task '$TaskName' does not expose exactly one recoverable -ConfigPath; inspect or repair it before generated-state removal."
    }
    $registered = $configPaths[0]
    if (-not (Test-S2DHciPathUnderRoot -Path $registered -Root $ConfigRoot)) {
        throw "Existing scheduled task '$TaskName' references a configuration path outside the trusted config directory: $registered"
    }
    return $registered
}

# Handle stop-s2dhcischeduledtaskpublisher for this module's workflow.
function Stop-S2DHciScheduledTaskPublisher {
    <#
    .SYNOPSIS
        Quiesce the scheduled collector before unregistering or deleting state.
    .DESCRIPTION
        Disables the root task so no new trigger can start, stops all currently
        running task instances, and verifies a bounded transition out of Running.
        If a later removal step fails, the remaining task stays disabled so a stale
        publisher cannot recreate generated state that was already selected for
        deletion.
    #>
    param(
        [Parameter(Mandatory)] [string]$TaskName,
        [ValidateRange(1, 120)] [int]$TimeoutSeconds = 30
    )

    $existingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop
    if (@($existingTask).Count -ne 1) {
        throw "Expected exactly one root scheduled task named '$TaskName' while quiescing removal."
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

    throw "Scheduled task '$TaskName' did not stop within $TimeoutSeconds seconds; task and generated state were not removed."
}

# Handle read-s2dhciconfiguredspoolfile for this module's workflow.
function Read-S2DHciConfiguredSpoolFile {
    <#
    .SYNOPSIS
        Read the configured virtualization spool file before deleting configuration.
    .DESCRIPTION
        Parses the non-secret generated configuration, requires a non-empty
        spool_file value, normalizes it, and rejects paths outside the trusted
        Checkmk spool directory. Invalid state fails closed instead of deleting an
        arbitrary path or silently leaving an unknown custom spool snapshot.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$SpoolRoot
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try { $config = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop }
    catch { throw "Generated spool configuration is invalid; refusing state removal until it is repaired or inspected: $Path" }
    if (-not ($config.PSObject.Properties.Name -contains 'spool_file') -or [string]::IsNullOrWhiteSpace([string]$config.spool_file)) {
        throw "Generated spool configuration has no valid spool_file: $Path"
    }
    $spoolFile = [System.IO.Path]::GetFullPath([string]$config.spool_file)
    if (-not (Test-S2DHciPathUnderRoot -Path $spoolFile -Root $SpoolRoot)) {
        throw "Generated configuration points outside the trusted spool directory: $spoolFile"
    }
    return $spoolFile
}

# Handle remove-s2dhcifileifpresent for this module's workflow.
function Remove-S2DHciFileIfPresent {
    <#
    .SYNOPSIS
        Remove one explicitly selected generated collector state file when present.
    .DESCRIPTION
        Performs an idempotent literal-path check and removes only the file passed
        by the caller. Normal task removal leaves generated state untouched unless
        the operator explicitly requests the RemoveGeneratedState lifecycle step.
    #>
    param([Parameter(Mandatory)] [string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) { Remove-Item -LiteralPath $Path -Force }
}

$root = [System.IO.Path]::GetFullPath($AgentRoot)
$configRoot = Join-Path $root 'config'
$spoolRoot = Join-Path $root 'spool'
$registeredConfigPath = $null
$configuredSpoolFile = $null
$spoolFiles = New-Object 'System.Collections.Generic.List[string]'

# Resolve and validate every generated-state dependency before stopping or
# unregistering the task. If recovery fails, the live task remains untouched and
# the operator can inspect/repair its state without orphaned custom configuration.
if ($RemoveGeneratedState) {
    $registeredConfigPath = Get-S2DHciRegisteredConfigPath -TaskName $TaskName -ConfigRoot $configRoot
    if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
        $ConfigPath = if ($null -ne $registeredConfigPath) {
            $registeredConfigPath
        } else {
            Join-Path $configRoot 's2d_hci_virtualization_spool.json'
        }
    }
    $ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
    if (-not (Test-S2DHciPathUnderRoot -Path $ConfigPath -Root $configRoot)) {
        throw "Generated spool configuration must remain below '$configRoot': $ConfigPath"
    }
    if ($null -ne $registeredConfigPath -and -not $registeredConfigPath.Equals($ConfigPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Existing scheduled task '$TaskName' uses ConfigPath '$registeredConfigPath', not '$ConfigPath'. Remove generated state using the registered path or omit -ConfigPath."
    }
    if ($null -ne $registeredConfigPath -and -not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Existing scheduled task '$TaskName' references missing configuration '$ConfigPath'; inspect or repair it before generated-state removal."
    }

    $configuredSpoolFile = Read-S2DHciConfiguredSpoolFile -Path $ConfigPath -SpoolRoot $spoolRoot
    if ($null -ne $configuredSpoolFile) { $spoolFiles.Add($configuredSpoolFile) }

    if (Test-Path -LiteralPath $spoolRoot -PathType Container) {
        Get-ChildItem -LiteralPath $spoolRoot -File -ErrorAction Stop | Where-Object {
            $_.Name -match '^\d+_s2d_hci_virtualization\.txt$'
        } | ForEach-Object {
            $candidate = [System.IO.Path]::GetFullPath($_.FullName)
            if (Test-S2DHciPathUnderRoot -Path $candidate -Root $spoolRoot) { $spoolFiles.Add($candidate) }
        }
    }
}

$existingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction SilentlyContinue
if ($null -ne $existingTask) {
    if (@($existingTask).Count -ne 1) {
        throw "Expected exactly one root scheduled task named '$TaskName'; inspect ambiguous task state before removal."
    }
    if ($PSCmdlet.ShouldProcess($TaskName, 'Quiesce scheduled collector before removal')) {
        Stop-S2DHciScheduledTaskPublisher -TaskName $TaskName
    }
    if ($PSCmdlet.ShouldProcess($TaskName, 'Unregister scheduled task')) {
        Unregister-ScheduledTask -TaskName $TaskName -TaskPath '\' -Confirm:$false
    }
}

if ($RemoveGeneratedState) {
    foreach ($path in @($spoolFiles | Sort-Object -Unique)) {
        if ($PSCmdlet.ShouldProcess($path, 'Remove generated virtualization spool snapshot')) {
            Remove-S2DHciFileIfPresent -Path $path
        }
    }
    if ($PSCmdlet.ShouldProcess($ConfigPath, 'Remove generated spool configuration')) {
        Remove-S2DHciFileIfPresent -Path $ConfigPath
    }
}
