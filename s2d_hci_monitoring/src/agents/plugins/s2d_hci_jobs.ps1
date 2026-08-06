#requires -Version 5.1
<#
.SYNOPSIS
    Storage jobs Checkmk collector for Windows S2D/HCI clusters.

.DESCRIPTION
    Emits active storage job data. Intended cache age: 300 seconds.
    This collector is read-only.
#>

$ErrorActionPreference = 'Stop'

function Write-JsonLine {
    param([Parameter(ValueFromPipeline)] [object] $InputObject)
    process {
        if ($null -ne $InputObject) {
            $InputObject | ConvertTo-Json -Compress -Depth 6
        }
    }
}

function Invoke-Section {
    param([string] $Name, [scriptblock] $ScriptBlock)
    Write-Output "<<<$Name>>>"
    try { & $ScriptBlock }
    catch { [pscustomobject]@{ section = $Name; success = $false; error = $_.Exception.Message } | Write-JsonLine }
}

Import-Module Storage -ErrorAction Stop

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
