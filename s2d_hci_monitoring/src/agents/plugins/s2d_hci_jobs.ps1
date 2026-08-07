#requires -Version 5.1
<#
.SYNOPSIS
    Storage jobs Checkmk collector for Windows S2D/HCI clusters.

.DESCRIPTION
    Emits active storage job data. Intended cache age: 300 seconds.
    This collector is read-only. Required-module startup failures are emitted through the same
    structured per-section failure protocol as command failures.
#>

$ErrorActionPreference = 'Stop'

function Write-JsonLine {
    <# Serialize one non-null object as a compact JSON line. #>
    param([Parameter(ValueFromPipeline)] [object] $InputObject)
    process {
        if ($null -ne $InputObject) {
            $InputObject | ConvertTo-Json -Compress -Depth 6
        }
    }
}

function Invoke-Section {
    <# Emit a Checkmk section and convert terminating command failures into structured telemetry. #>
    param([string] $Name, [scriptblock] $ScriptBlock)
    Write-Output "<<<$Name>>>"
    try { & $ScriptBlock }
    catch { [pscustomobject]@{ section = $Name; success = $false; error = $_.Exception.Message } | Write-JsonLine }
}

function Import-CollectorModules {
    <# Import required modules or emit a failure row for every affected section and stop cleanly. #>
    param(
        [Parameter(Mandatory)] [string[]] $ModuleName,
        [Parameter(Mandatory)] [string[]] $SectionName
    )

    try {
        foreach ($module in $ModuleName) {
            Import-Module $module -ErrorAction Stop
        }
    }
    catch {
        $message = "Required module import failed: $($_.Exception.Message)"
        foreach ($section in $SectionName) {
            Write-Output "<<<$section>>>"
            [pscustomobject]@{ section = $section; success = $false; error = $message } | Write-JsonLine
        }
        exit 0
    }
}

Import-CollectorModules -ModuleName @('Storage') -SectionName @('s2d_hci_storage_jobs')

Invoke-Section -Name 's2d_hci_storage_jobs' -ScriptBlock {
    Get-StorageJob | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            is_background_task = $_.IsBackgroundTask
            job_state = $_.JobState.ToString()
            percent_complete = $_.PercentComplete
            bytes_processed = $_.BytesProcessed
            bytes_total = $_.BytesTotal
            elapsed_time = $_.ElapsedTime.ToString()
            recovery_action = $_.RecoveryAction
        }
    } | Write-JsonLine
}
