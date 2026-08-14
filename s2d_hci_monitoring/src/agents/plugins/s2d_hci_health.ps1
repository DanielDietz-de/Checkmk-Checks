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
$pluginRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $pluginRoot))
if ((Split-Path -Leaf $agentRoot) -ieq 'plugins') {
    $agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $agentRoot))
}
Import-Module (Join-Path $agentRoot 'bin\s2d_hci_common.psm1') -Force -ErrorAction Stop
$config = Get-S2DHciConfig -AgentRoot $agentRoot
$context = New-S2DHciRunContext -Collector 'health' -Config $config
$piggybackOpen = $false

function Test-S2DHciCommandAvailable {
    <#
    .SYNOPSIS
        Test whether a required or optional PowerShell command is available.
    .DESCRIPTION
        Looks up the command without throwing and returns a Boolean. Collectors
        use this helper to distinguish unsupported Windows features from runtime
        command failures so unsupported telemetry can be reported as UNKNOWN.
    #>
    param([Parameter(Mandatory)] [string]$Name)

    return $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Get-S2DHciPropertyValue {
    <#
    .SYNOPSIS
        Read the first available property from vendor objects with varying schemas.
    .DESCRIPTION
        Checks candidate property names in order and returns the first non-null
        value. This keeps S2D normalization compatible with Windows cmdlet output
        that varies by Server release without silently inventing a value.
    #>
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
    <#
    .SYNOPSIS
        Normalize native S2D cmdlet output into the package protocol schema.
    .DESCRIPTION
        Extracts state, health, operational status, and cache information from
        version-dependent Microsoft objects and emits stable lower-case fields.
        Missing fields remain explicit instead of causing a false healthy state.
    #>
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

        $sectionName = 's2d_hci_s2d_state'
        try {
            if (Test-S2DHciCommandAvailable -Name 'Get-ClusterStorageSpacesDirect') {
                Get-ClusterStorageSpacesDirect -ErrorAction Stop | ForEach-Object {
                    ConvertTo-S2DHciStateRecord -InputObject $_ -SourceCommand 'Get-ClusterStorageSpacesDirect'
                } | Write-S2DHciSection -Name $sectionName -Context $context
            }
            elseif (Test-S2DHciCommandAvailable -Name 'Get-ClusterS2D') {
                Get-ClusterS2D -ErrorAction Stop | ForEach-Object {
                    ConvertTo-S2DHciStateRecord -InputObject $_ -SourceCommand 'Get-ClusterS2D'
                } | Write-S2DHciSection -Name $sectionName -Context $context
            }
            else {
                $unavailable = [pscustomobject]@{
                    name = 'Storage Spaces Direct'
                    available = $false
                    reason = 'No supported S2D state command is available.'
                }
                $unavailable | Write-S2DHciSection -Name $sectionName -Context $context
            }
        }
        catch {
            Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_
        }

        $sectionName = 's2d_hci_storage_subsystems'
        try {
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
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch {
            Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_
        }

        $sectionName = 's2d_hci_storage_health_report'
        try {
            if (-not (Test-S2DHciCommandAvailable -Name 'Get-StorageHealthReport')) {
                $unavailable = [pscustomobject]@{
                    name = 'Storage health report'
                    available = $false
                    reason = 'Get-StorageHealthReport is not available.'
                }
                $unavailable | Write-S2DHciSection -Name $sectionName -Context $context
            }
            else {
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
                        [pscustomobject]@{
                            subsystem = [string]$subsystem.FriendlyName
                            success = $false
                            error = $_.Exception.Message
                        }
                    }
                } | Write-S2DHciSection -Name $sectionName -Context $context
            }
        }
        catch {
            Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_
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
