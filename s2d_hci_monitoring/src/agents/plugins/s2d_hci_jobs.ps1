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
try {
    $config = Get-S2DHciConfig -AgentRoot $agentRoot
}
catch {
    $message = "Configuration validation failed: $($_.Exception.Message)"
    if ($message.Length -gt 512) { $message = $message.Substring(0, 512) + ' [truncated]' }
    $now = [DateTime]::UtcNow.ToString('o')
    Write-Output '<<<s2d_hci_collector_health>>>'
    [ordered]@{
        protocol_version = 1
        run_id = [guid]::NewGuid().Guid
        collector = 'jobs'
        success = $false
        complete = $false
        truncated = $false
        record_count = 0
        output_bytes = 0
        max_records = 2000
        max_output_bytes = 1048576
        max_runtime_seconds = 120
        elapsed_ms = 0
        role = 'local'
        cluster_name = $null
        logical_host = $null
        source_host = $env:COMPUTERNAME
        errors = @($message)
        started_at = $now
        finished_at = $now
    } | ConvertTo-Json -Compress -Depth 6
    return
}
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
