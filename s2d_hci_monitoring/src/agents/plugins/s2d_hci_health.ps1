#requires -Version 5.1
<#
.SYNOPSIS
    Health Checkmk collector for Windows S2D/HCI clusters.

.DESCRIPTION
    Emits S2D and storage health report data. Intended cache age: 600 seconds.
    This collector is read-only.
#>

$ErrorActionPreference = 'Stop'

function Write-JsonLine {
    param([Parameter(ValueFromPipeline)] [object] $InputObject)
    process {
        if ($null -ne $InputObject) {
            $InputObject | ConvertTo-Json -Compress -Depth 8
        }
    }
}

function Invoke-Section {
    param([string] $Name, [scriptblock] $ScriptBlock)
    Write-Output "<<<$Name>>>"
    try { & $ScriptBlock }
    catch { [pscustomobject]@{ section = $Name; success = $false; error = $_.Exception.Message } | Write-JsonLine }
}

function Test-CommandAvailable {
    param([Parameter(Mandatory)] [string] $Name)
    $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

Import-Module FailoverClusters -ErrorAction Stop
Import-Module Storage -ErrorAction Stop

Invoke-Section -Name 's2d_hci_s2d_state' -ScriptBlock {
    if (Test-CommandAvailable -Name 'Get-ClusterStorageSpacesDirect') {
        Get-ClusterStorageSpacesDirect | Write-JsonLine
    }
    elseif (Test-CommandAvailable -Name 'Get-ClusterS2D') {
        Get-ClusterS2D | Write-JsonLine
    }
    else {
        [pscustomobject]@{ available = $false; reason = 'No S2D cluster cmdlet is available on this system.' } | Write-JsonLine
    }
}

Invoke-Section -Name 's2d_hci_storage_subsystems' -ScriptBlock {
    Get-StorageSubSystem | Sort-Object FriendlyName | ForEach-Object {
        [pscustomobject]@{
            friendly_name = $_.FriendlyName
            health_status = $_.HealthStatus.ToString()
            operational_status = ($_.OperationalStatus -join ',')
            model = $_.Model
            manufacturer = $_.Manufacturer
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_storage_health_report' -ScriptBlock {
    if (Test-CommandAvailable -Name 'Get-StorageHealthReport') {
        Get-StorageSubSystem | ForEach-Object {
            try {
                $_ | Get-StorageHealthReport | Write-JsonLine
            }
            catch {
                [pscustomobject]@{ subsystem = $_.FriendlyName; success = $false; error = $_.Exception.Message } | Write-JsonLine
            }
        }
    }
    else {
        [pscustomobject]@{ available = $false; reason = 'Get-StorageHealthReport is not available on this system.' } | Write-JsonLine
    }
}
