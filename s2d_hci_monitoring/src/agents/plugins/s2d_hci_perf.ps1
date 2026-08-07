#requires -Version 5.1
<#
.SYNOPSIS
    Performance-history Checkmk collector for Windows S2D/HCI clusters.

.DESCRIPTION
    Emits optional cluster performance history if supported. Intended cache age: 900 seconds.
    This collector is read-only. Required-module startup failures are emitted through the same
    structured per-section failure protocol as command failures.
#>

$ErrorActionPreference = 'Stop'

function Write-JsonLine {
    <# Serialize one non-null object as a compact JSON line. #>
    param([Parameter(ValueFromPipeline)] [object] $InputObject)
    process {
        if ($null -ne $InputObject) {
            $InputObject | ConvertTo-Json -Compress -Depth 8
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

Import-CollectorModules -ModuleName @('FailoverClusters') -SectionName @('s2d_hci_performance_history')

Invoke-Section -Name 's2d_hci_performance_history' -ScriptBlock {
    if ($null -ne (Get-Command -Name 'Get-ClusterPerformanceHistory' -ErrorAction SilentlyContinue)) {
        Get-ClusterPerformanceHistory | Write-JsonLine
    }
    else {
        [pscustomobject]@{ available = $false; reason = 'Get-ClusterPerformanceHistory is not available on this system.' } | Write-JsonLine
    }
}
