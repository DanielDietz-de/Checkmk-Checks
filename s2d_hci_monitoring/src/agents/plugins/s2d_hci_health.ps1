#requires -Version 5.1
<#
.SYNOPSIS
    Bounded S2D and storage-health collector.
.DESCRIPTION
    Runs on the elected cluster node, normalizes optional S2D command output,
    and emits curated health telemetry to the logical cluster piggyback host.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
Import-Module (Join-Path $agentRoot 'bin\s2d_hci_common.psm1') -Force -ErrorAction Stop
$config = Get-S2DHciConfig -AgentRoot $agentRoot
$context = New-S2DHciRunContext -Collector 'health' -Config $config
$piggybackOpen = $false

function Test-S2DHciCommandAvailable {
    <# Return whether a named PowerShell command is available in this session. #>
    param([Parameter(Mandatory)] [string]$Name)

    return $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Get-S2DHciPropertyValue {
    <# Return the first non-null property value from a list of candidate names. #>
    param(
        [Parameter(Mandatory)] [object]$InputObject,
        [Parameter(Mandatory)] [string[]]$Names
    )

    foreach ($name in $Names) {
        $property = $InputObject.PSObject.Properties[$name]
        if ($null -ne $property -and $null -ne $property.Value) { return $property.Value }
    }
    return $null
}

function ConvertTo-S2DHciStateRecord {
    <# Normalize native S2D command output into the stable protocol schema. #>
    param(
        [Parameter(Mandatory)] [object]$InputObject,
        [Parameter(Mandatory)] [string]$SourceCommand
    )

    $nativeState = Get-S2DHciPropertyValue -InputObject $InputObject -Names @('State', 'HealthStatus', 'OperationalStatus')
    $enabled = Get-S2DHciPropertyValue -InputObject $InputObject -Names @('Enabled', 'S2DEnabled')
    if ($null -eq $nativeState -and $null -ne $enabled) {
        $nativeState = if ([System.Convert]::ToBoolean($enabled)) { 'Enabled' } else { 'Disabled' }
    }
    if ($nativeState -is [System.Array]) { $nativeState = $nativeState -join ',' }

    return [pscustomobject]@{
        name = 'Storage Spaces Direct'
        available = $true
        source_command = $SourceCommand
        state = if ($null -ne $nativeState) { [string]$nativeState } else { 'unknown' }
        health_status = [string](Get-S2DHciPropertyValue -InputObject $InputObject -Names @('HealthStatus'))
        operational_status = [string]((Get-S2DHciPropertyValue -InputObject $InputObject -Names @('OperationalStatus')) -join ',')
        cache_state = [string](Get-S2DHciPropertyValue -InputObject $InputObject -Names @('CacheState'))
    }
}

try {
    Import-Module FailoverClusters -ErrorAction Stop
    Import-Module Storage -ErrorAction Stop
    $clusterContext = Get-S2DHciClusterContext -Context $context
    if ($clusterContext.IsLeader) {
        Start-S2DHciPiggyback -HostName $clusterContext.LogicalHost
        $piggybackOpen = $true

        Write-S2DHciSection -Name 's2d_hci_s2d_state' -Context $context -ScriptBlock {
            if (Test-S2DHciCommandAvailable -Name 'Get-ClusterStorageSpacesDirect') {
                Get-ClusterStorageSpacesDirect -ErrorAction Stop | ForEach-Object {
                    ConvertTo-S2DHciStateRecord -InputObject $_ -SourceCommand 'Get-ClusterStorageSpacesDirect'
                }
            }
            elseif (Test-S2DHciCommandAvailable -Name 'Get-ClusterS2D') {
                Get-ClusterS2D -ErrorAction Stop | ForEach-Object {
                    ConvertTo-S2DHciStateRecord -InputObject $_ -SourceCommand 'Get-ClusterS2D'
                }
            }
            else {
                [pscustomobject]@{ name = 'Storage Spaces Direct'; available = $false; reason = 'No supported S2D state command is available.' }
            }
        }

        Write-S2DHciSection -Name 's2d_hci_storage_subsystems' -Context $context -ScriptBlock {
            Get-StorageSubSystem -ErrorAction Stop | Sort-Object FriendlyName | ForEach-Object {
                $source = if ($_.UniqueId) { [string]$_.UniqueId } elseif ($_.ObjectId) { [string]$_.ObjectId } else { [string]$_.FriendlyName }
                [pscustomobject]@{
                    identity = "subsystem-$(Get-S2DHciStableHash -Value $source)"
                    friendly_name = [string]$_.FriendlyName
                    health_status = $_.HealthStatus.ToString()
                    operational_status = ($_.OperationalStatus -join ',')
                    model = [string]$_.Model
                    manufacturer = [string]$_.Manufacturer
                }
            }
        }

        Write-S2DHciSection -Name 's2d_hci_storage_health_report' -Context $context -ScriptBlock {
            if (-not (Test-S2DHciCommandAvailable -Name 'Get-StorageHealthReport')) {
                [pscustomobject]@{ name = 'Storage health report'; available = $false; reason = 'Get-StorageHealthReport is not available.' }
                return
            }
            Get-StorageSubSystem -ErrorAction Stop | ForEach-Object {
                $subsystem = $_
                try {
                    $report = $subsystem | Get-StorageHealthReport -ErrorAction Stop
                    [pscustomobject]@{
                        identity = "health-$(Get-S2DHciStableHash -Value ([string]$subsystem.FriendlyName))"
                        subsystem = [string]$subsystem.FriendlyName
                        health_status = [string](Get-S2DHciPropertyValue -InputObject $report -Names @('HealthStatus', 'HealthState', 'State'))
                        operational_status = [string]((Get-S2DHciPropertyValue -InputObject $report -Names @('OperationalStatus', 'OperationalState')) -join ',')
                        severity = [string](Get-S2DHciPropertyValue -InputObject $report -Names @('Severity'))
                    }
                }
                catch {
                    [pscustomobject]@{ subsystem = [string]$subsystem.FriendlyName; success = $false; error = $_.Exception.Message }
                }
            }
        }
    }
}
catch {
    Add-S2DHciCollectorError -Context $context -Message "health startup: $($_.Exception.Message)"
}
finally {
    if ($piggybackOpen) { Stop-S2DHciPiggyback }
    Write-S2DHciCollectorHealth -Context $context
}
