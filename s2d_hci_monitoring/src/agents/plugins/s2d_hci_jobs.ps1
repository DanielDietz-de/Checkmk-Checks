#requires -Version 5.1
<#
.SYNOPSIS
    Bounded storage-job collector for S2D/HCI monitoring.
.DESCRIPTION
    Runs only on the elected cluster collector, emits storage jobs to the
    logical cluster piggyback host, and reports explicit collector health.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
Import-Module (Join-Path $agentRoot 'bin\s2d_hci_common.psm1') -Force -ErrorAction Stop
$config = Get-S2DHciConfig -AgentRoot $agentRoot
$context = New-S2DHciRunContext -Collector 'jobs' -Config $config
$piggybackOpen = $false

try {
    Import-Module FailoverClusters -ErrorAction Stop
    Import-Module Storage -ErrorAction Stop
    $clusterContext = Get-S2DHciClusterContext -Context $context
    if ($clusterContext.IsLeader) {
        Start-S2DHciPiggyback -HostName $clusterContext.LogicalHost
        $piggybackOpen = $true
        $sectionName = 's2d_hci_storage_jobs'
        try {
            Get-StorageJob -ErrorAction Stop | Sort-Object Name | ForEach-Object {
                [pscustomobject]@{
                    identity = "job-$(Get-S2DHciStableHash -Value ([string]$_.Name))"
                    name = [string]$_.Name
                    is_background_task = $_.IsBackgroundTask
                    job_state = $_.JobState.ToString()
                    percent_complete = $_.PercentComplete
                    bytes_processed = $_.BytesProcessed
                    bytes_total = $_.BytesTotal
                    elapsed_seconds = [int64]$_.ElapsedTime.TotalSeconds
                    recovery_action = [string]$_.RecoveryAction
                }
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }
    }
}
catch {
    Add-S2DHciCollectorError -Context $context -Message "jobs startup: $($_.Exception.Message)"
}
finally {
    if ($piggybackOpen) { Stop-S2DHciPiggyback }
    Write-S2DHciCollectorHealth -Context $context
}
