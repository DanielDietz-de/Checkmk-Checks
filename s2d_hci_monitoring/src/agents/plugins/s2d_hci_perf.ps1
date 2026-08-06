#requires -Version 5.1
<#
.SYNOPSIS
    Performance-history Checkmk collector for Windows S2D/HCI clusters.

.DESCRIPTION
    Emits optional cluster performance history if supported. Intended cache age: 900 seconds.
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

Import-Module FailoverClusters -ErrorAction Stop

Invoke-Section -Name 's2d_hci_performance_history' -ScriptBlock {
    if ($null -ne (Get-Command -Name 'Get-ClusterPerformanceHistory' -ErrorAction SilentlyContinue)) {
        Get-ClusterPerformanceHistory | Write-JsonLine
    }
    else {
        [pscustomobject]@{ available = $false; reason = 'Get-ClusterPerformanceHistory is not available on this system.' } | Write-JsonLine
    }
}
