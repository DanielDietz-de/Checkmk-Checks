#requires -Version 5.1
<#
.SYNOPSIS
    Remove the S2D/HCI gMSA scheduled task and optional generated state.
.DESCRIPTION
    Removes only the named task and, when explicitly requested, reads the current
    generated spool configuration before removing it, deletes that configured
    spool snapshot plus any package-standard derived-lifetime snapshots, and then
    removes the configuration. Packaged collector files are left to the Checkmk
    agent package lifecycle. Every mutation honors ShouldProcess.
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

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess($TaskName, 'Unregister scheduled task')) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
}

if ($RemoveGeneratedState) {
    $root = [System.IO.Path]::GetFullPath($AgentRoot)
    $configRoot = Join-Path $root 'config'
    $spoolRoot = Join-Path $root 'spool'
    if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
        $ConfigPath = Join-Path $configRoot 's2d_hci_virtualization_spool.json'
    }
    $ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
    if (-not (Test-S2DHciPathUnderRoot -Path $ConfigPath -Root $configRoot)) {
        throw "Generated spool configuration must remain below '$configRoot': $ConfigPath"
    }

    $configuredSpoolFile = Read-S2DHciConfiguredSpoolFile -Path $ConfigPath -SpoolRoot $spoolRoot
    $spoolFiles = New-Object 'System.Collections.Generic.List[string]'
    if ($null -ne $configuredSpoolFile) { $spoolFiles.Add($configuredSpoolFile) }

    if (Test-Path -LiteralPath $spoolRoot -PathType Container) {
        Get-ChildItem -LiteralPath $spoolRoot -File -ErrorAction Stop | Where-Object {
            $_.Name -match '^\d+_s2d_hci_virtualization\.txt$'
        } | ForEach-Object {
            $candidate = [System.IO.Path]::GetFullPath($_.FullName)
            if (Test-S2DHciPathUnderRoot -Path $candidate -Root $spoolRoot) { $spoolFiles.Add($candidate) }
        }
    }

    foreach ($path in @($spoolFiles | Sort-Object -Unique)) {
        if ($PSCmdlet.ShouldProcess($path, 'Remove generated virtualization spool snapshot')) {
            Remove-S2DHciFileIfPresent -Path $path
        }
    }
    if ($PSCmdlet.ShouldProcess($ConfigPath, 'Remove generated spool configuration')) {
        Remove-S2DHciFileIfPresent -Path $ConfigPath
    }
}
