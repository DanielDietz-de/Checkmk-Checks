#requires -Version 5.1
<#
.SYNOPSIS
    Bounded cluster-state collector for S2D/HCI monitoring.
.DESCRIPTION
    Elects one healthy cluster node, emits cluster-wide data to a stable logical
    piggyback host, and always emits collector-health telemetry on the physical
    source node. The collector is read-only.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
Import-Module (Join-Path $agentRoot 'bin\s2d_hci_common.psm1') -Force -ErrorAction Stop
$config = Get-S2DHciConfig -AgentRoot $agentRoot
$context = New-S2DHciRunContext -Collector 'fast' -Config $config
$piggybackOpen = $false

try {
    Import-Module FailoverClusters -ErrorAction Stop
    $clusterContext = Get-S2DHciClusterContext -Context $context
    if ($clusterContext.IsLeader) {
        Start-S2DHciPiggyback -HostName $clusterContext.LogicalHost
        $piggybackOpen = $true

        Write-S2DHciSection -Name 's2d_hci_cluster_summary' -Context $context -ScriptBlock {
            Get-Cluster -ErrorAction Stop | ForEach-Object {
                [pscustomobject]@{
                    name = [string]$_.Name
                    domain = [string]$_.Domain
                    owner_node = [string]$_.OwnerNode.Name
                    dynamic_quorum = $_.DynamicQuorum
                }
            }
        }

        Write-S2DHciSection -Name 's2d_hci_quorum' -Context $context -ScriptBlock {
            Get-ClusterQuorum -ErrorAction Stop | ForEach-Object {
                [pscustomobject]@{
                    quorum_type = $_.QuorumType.ToString()
                    quorum_resource = if ($_.QuorumResource) { [string]$_.QuorumResource.Name } else { $null }
                    quorum_resource_state = if ($_.QuorumResource) { $_.QuorumResource.State.ToString() } else { $null }
                }
            }
        }

        Write-S2DHciSection -Name 's2d_hci_nodes' -Context $context -ScriptBlock {
            Get-ClusterNode -ErrorAction Stop | Sort-Object Id | ForEach-Object {
                [pscustomobject]@{
                    name = [string]$_.Name
                    id = [string]$_.Id
                    state = $_.State.ToString()
                    node_weight = $_.NodeWeight
                    dynamic_weight = $_.DynamicWeight
                    drain_status = $_.DrainStatus.ToString()
                }
            }
        }

        Write-S2DHciSection -Name 's2d_hci_networks' -Context $context -ScriptBlock {
            Get-ClusterNetwork -ErrorAction Stop | Sort-Object Name | ForEach-Object {
                $record = [ordered]@{
                    name = [string]$_.Name
                    role = $_.Role.ToString()
                    state = $_.State.ToString()
                    metric = $_.Metric
                    auto_metric = $_.AutoMetric
                }
                if ($config.include_addresses) { $record.address = [string]$_.Address }
                [pscustomobject]$record
            }
        }

        Write-S2DHciSection -Name 's2d_hci_network_interfaces' -Context $context -ScriptBlock {
            Get-ClusterNetworkInterface -ErrorAction Stop | Sort-Object Node, Name | ForEach-Object {
                $node = [string]$_.Node
                $name = [string]$_.Name
                $record = [ordered]@{
                    identity = "$node / $name"
                    name = $name
                    node = $node
                    network = [string]$_.Network
                    adapter = [string]$_.Adapter
                    state = $_.State.ToString()
                }
                if ($config.include_addresses) { $record.address = [string]$_.Address }
                [pscustomobject]$record
            }
        }

        Write-S2DHciSection -Name 's2d_hci_cluster_groups' -Context $context -ScriptBlock {
            Get-ClusterGroup -ErrorAction Stop | Sort-Object Name | ForEach-Object {
                [pscustomobject]@{
                    name = [string]$_.Name
                    group_type = $_.GroupType.ToString()
                    owner_node = [string]$_.OwnerNode.Name
                    state = $_.State.ToString()
                    priority = $_.Priority
                }
            }
        }

        Write-S2DHciSection -Name 's2d_hci_cluster_resources' -Context $context -ScriptBlock {
            Get-ClusterResource -ErrorAction Stop | Sort-Object OwnerGroup, Name | ForEach-Object {
                [pscustomobject]@{
                    name = [string]$_.Name
                    resource_type = [string]$_.ResourceType
                    owner_group = [string]$_.OwnerGroup.Name
                    owner_node = [string]$_.OwnerNode.Name
                    state = $_.State.ToString()
                }
            }
        }
    }
}
catch {
    Add-S2DHciCollectorError -Context $context -Message "fast startup: $($_.Exception.Message)"
}
finally {
    if ($piggybackOpen) { Stop-S2DHciPiggyback }
    Write-S2DHciCollectorHealth -Context $context
}
