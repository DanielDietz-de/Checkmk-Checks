#requires -Version 5.1
<#
.SYNOPSIS
    Fast Checkmk collector for Windows S2D/HCI cluster state.

.DESCRIPTION
    Emits fast-changing cluster state sections for Checkmk. Intended cache age: 60-120 seconds.
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
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [scriptblock] $ScriptBlock
    )
    Write-Output "<<<$Name>>>"
    try {
        & $ScriptBlock
    }
    catch {
        [pscustomobject]@{ section = $Name; success = $false; error = $_.Exception.Message } | Write-JsonLine
    }
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

Import-CollectorModules -ModuleName @('FailoverClusters') -SectionName @(
    's2d_hci_cluster_summary',
    's2d_hci_quorum',
    's2d_hci_nodes',
    's2d_hci_networks',
    's2d_hci_network_interfaces',
    's2d_hci_cluster_groups',
    's2d_hci_cluster_resources'
)

Invoke-Section -Name 's2d_hci_cluster_summary' -ScriptBlock {
    Get-Cluster | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            domain = $_.Domain
            owner_node = $_.OwnerNode.Name
            dynamic_quorum = $_.DynamicQuorum
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_quorum' -ScriptBlock {
    Get-ClusterQuorum | ForEach-Object {
        [pscustomobject]@{
            quorum_type = $_.QuorumType.ToString()
            quorum_resource = if ($_.QuorumResource) { $_.QuorumResource.Name } else { $null }
            quorum_resource_state = if ($_.QuorumResource) { $_.QuorumResource.State.ToString() } else { $null }
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_nodes' -ScriptBlock {
    Get-ClusterNode | Sort-Object Id | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            id = $_.Id
            state = $_.State.ToString()
            node_weight = $_.NodeWeight
            dynamic_weight = $_.DynamicWeight
            drain_status = $_.DrainStatus.ToString()
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_networks' -ScriptBlock {
    Get-ClusterNetwork | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            address = $_.Address
            role = $_.Role.ToString()
            state = $_.State.ToString()
            metric = $_.Metric
            auto_metric = $_.AutoMetric
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_network_interfaces' -ScriptBlock {
    Get-ClusterNetworkInterface | Sort-Object Node, Name | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            node = $_.Node
            network = $_.Network
            adapter = $_.Adapter
            address = $_.Address
            state = $_.State.ToString()
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_cluster_groups' -ScriptBlock {
    Get-ClusterGroup | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            group_type = $_.GroupType.ToString()
            owner_node = $_.OwnerNode.Name
            state = $_.State.ToString()
            priority = $_.Priority
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_cluster_resources' -ScriptBlock {
    Get-ClusterResource | Sort-Object OwnerGroup, Name | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            resource_type = $_.ResourceType
            owner_group = $_.OwnerGroup.Name
            owner_node = $_.OwnerNode.Name
            state = $_.State.ToString()
        }
    } | Write-JsonLine
}
