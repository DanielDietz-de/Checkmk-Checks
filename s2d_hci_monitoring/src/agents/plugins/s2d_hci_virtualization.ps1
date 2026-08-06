#requires -Version 5.1
<#
.SYNOPSIS
    Read-only virtualization workload collector for Windows cluster nodes.

.DESCRIPTION
    Emits host and workload state sections for Checkmk. Intended cache age: 120-300 seconds.
    This collector is read-only and must not change workload, host, cluster, or storage state.
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

function Test-CommandAvailable {
    param([Parameter(Mandatory)] [string] $Name)
    $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

Invoke-Section -Name 's2d_hci_virtualization_host' -ScriptBlock {
    $service = Get-Service -Name 'vmms' -ErrorAction SilentlyContinue
    [pscustomobject]@{
        name = $env:COMPUTERNAME
        service_status = if ($service) { $service.Status.ToString() } else { 'NotFound' }
        service_start_type = if ($service) { $service.StartType.ToString() } else { $null }
        module_available = Test-CommandAvailable -Name 'Get-VM'
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_virtualization_workloads' -ScriptBlock {
    Import-Module Hyper-V -ErrorAction Stop
    Get-VM | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            id = $_.VMId.Guid
            state = $_.State.ToString()
            status = $_.Status
            generation = $_.Generation
            uptime_seconds = [int64]$_.Uptime.TotalSeconds
            cpu_usage = $_.CPUUsage
            memory_assigned = $_.MemoryAssigned
            memory_demand = $_.MemoryDemand
            memory_status = $_.MemoryStatus
            dynamic_memory_enabled = $_.DynamicMemoryEnabled
            processor_count = $_.ProcessorCount
            automatic_start_action = $_.AutomaticStartAction.ToString()
            automatic_stop_action = $_.AutomaticStopAction.ToString()
            configuration_version = $_.ConfigurationVersion.ToString()
            path = $_.Path
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_virtualization_services' -ScriptBlock {
    Import-Module Hyper-V -ErrorAction Stop
    Get-VM | Sort-Object Name | ForEach-Object {
        $workload = $_
        Get-VMIntegrationService -VMName $workload.Name | Sort-Object Name | ForEach-Object {
            [pscustomobject]@{
                name = "$($workload.Name) / $($_.Name)"
                workload_name = $workload.Name
                service_name = $_.Name
                enabled = $_.Enabled
                primary_status_description = $_.PrimaryStatusDescription
                secondary_status_description = $_.SecondaryStatusDescription
            }
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_virtualization_replication' -ScriptBlock {
    Import-Module Hyper-V -ErrorAction Stop
    if (Test-CommandAvailable -Name 'Get-VMReplication') {
        Get-VMReplication | Sort-Object VMName | ForEach-Object {
            [pscustomobject]@{
                name = $_.VMName
                state = $_.State.ToString()
                health = $_.Health.ToString()
                mode = $_.Mode.ToString()
                frequency_sec = $_.FrequencySec
                last_replication_time = $_.LastReplicationTime
                primary_server = $_.PrimaryServer
                replica_server = $_.ReplicaServer
            }
        } | Write-JsonLine
    }
    else {
        [pscustomobject]@{ name = 'replication'; available = $false; reason = 'Replication command is not available on this system.' } | Write-JsonLine
    }
}

Invoke-Section -Name 's2d_hci_virtualization_checkpoints' -ScriptBlock {
    Import-Module Hyper-V -ErrorAction Stop
    Get-VM | Sort-Object Name | ForEach-Object {
        $workload = $_
        Get-VMSnapshot -VMName $workload.Name -ErrorAction SilentlyContinue | Sort-Object CreationTime | ForEach-Object {
            [pscustomobject]@{
                name = "$($workload.Name) / $($_.Name)"
                workload_name = $workload.Name
                checkpoint_name = $_.Name
                checkpoint_type = $_.CheckpointType.ToString()
                creation_time = $_.CreationTime.ToUniversalTime().ToString('o')
            }
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_virtualization_network_adapters' -ScriptBlock {
    Import-Module Hyper-V -ErrorAction Stop
    Get-VM | Sort-Object Name | ForEach-Object {
        $workload = $_
        Get-VMNetworkAdapter -VMName $workload.Name | Sort-Object Name | ForEach-Object {
            [pscustomobject]@{
                name = "$($workload.Name) / $($_.Name)"
                workload_name = $workload.Name
                adapter_name = $_.Name
                switch_name = $_.SwitchName
                connected = $_.Connected
                status = $_.Status
                mac_address = $_.MacAddress
                ip_addresses = ($_.IPAddresses -join ',')
                vlan_mode = $_.VlanSetting.OperationMode.ToString()
            }
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_virtualization_hard_disks' -ScriptBlock {
    Import-Module Hyper-V -ErrorAction Stop
    Get-VM | Sort-Object Name | ForEach-Object {
        $workload = $_
        Get-VMHardDiskDrive -VMName $workload.Name | Sort-Object Path | ForEach-Object {
            $vhd = $null
            try {
                if (Test-CommandAvailable -Name 'Get-VHD') {
                    $vhd = Get-VHD -Path $_.Path -ErrorAction Stop
                }
            }
            catch {
                $vhd = $null
            }
            [pscustomobject]@{
                name = "$($workload.Name) / $($_.ControllerType)$($_.ControllerNumber):$($_.ControllerLocation)"
                workload_name = $workload.Name
                path = $_.Path
                controller_type = $_.ControllerType.ToString()
                controller_number = $_.ControllerNumber
                controller_location = $_.ControllerLocation
                disk_number = $_.DiskNumber
                vhd_type = if ($vhd) { $vhd.VhdType.ToString() } else { $null }
                vhd_format = if ($vhd) { $vhd.VhdFormat.ToString() } else { $null }
                size = if ($vhd) { $vhd.Size } else { $null }
                file_size = if ($vhd) { $vhd.FileSize } else { $null }
                minimum_size = if ($vhd) { $vhd.MinimumSize } else { $null }
                parent_path = if ($vhd) { $vhd.ParentPath } else { $null }
            }
        }
    } | Write-JsonLine
}
