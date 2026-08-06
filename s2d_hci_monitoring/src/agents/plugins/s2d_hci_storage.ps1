#requires -Version 5.1
<#
.SYNOPSIS
    Storage Checkmk collector for Windows S2D/HCI clusters.

.DESCRIPTION
    Emits CSV, pool, virtual disk, volume, and physical disk sections. Intended cache age: 300 seconds.
    This collector is read-only.
#>

$ErrorActionPreference = 'Stop'

function Write-JsonLine {
    param([Parameter(ValueFromPipeline)] [object] $InputObject)
    process {
        if ($null -ne $InputObject) {
            $InputObject | ConvertTo-Json -Compress -Depth 6
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
Import-Module Storage -ErrorAction Stop

Invoke-Section -Name 's2d_hci_csv' -ScriptBlock {
    Get-ClusterSharedVolume | Sort-Object Name | ForEach-Object {
        $csv = $_
        foreach ($info in $csv.SharedVolumeInfo) {
            $partition = $info.Partition
            [pscustomobject]@{
                name = $csv.Name
                owner_node = $csv.OwnerNode.Name
                state = $csv.State.ToString()
                friendly_volume_name = $info.FriendlyVolumeName
                filesystem = $partition.FileSystem
                size = $partition.Size
                free_space = $partition.FreeSpace
                percent_free = if ($partition.Size -gt 0) { [math]::Round(($partition.FreeSpace / $partition.Size) * 100, 2) } else { $null }
            }
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_storage_pools' -ScriptBlock {
    Get-StoragePool | Where-Object { -not $_.IsPrimordial } | Sort-Object FriendlyName | ForEach-Object {
        [pscustomobject]@{
            friendly_name = $_.FriendlyName
            health_status = $_.HealthStatus.ToString()
            operational_status = ($_.OperationalStatus -join ',')
            size = $_.Size
            allocated_size = $_.AllocatedSize
            usage = $_.Usage.ToString()
            is_read_only = $_.IsReadOnly
            is_clustered = $_.IsClustered
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_virtual_disks' -ScriptBlock {
    Get-VirtualDisk | Sort-Object FriendlyName | ForEach-Object {
        [pscustomobject]@{
            friendly_name = $_.FriendlyName
            health_status = $_.HealthStatus.ToString()
            operational_status = ($_.OperationalStatus -join ',')
            detached_reason = $_.DetachedReason
            size = $_.Size
            allocated_size = $_.AllocatedSize
            footprint_on_pool = $_.FootprintOnPool
            resiliency_setting_name = $_.ResiliencySettingName
            provisioning_type = $_.ProvisioningType.ToString()
            physical_disk_redundancy = $_.PhysicalDiskRedundancy
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_volumes' -ScriptBlock {
    Get-Volume | Sort-Object FileSystemLabel, DriveLetter | ForEach-Object {
        [pscustomobject]@{
            filesystem_label = $_.FileSystemLabel
            drive_letter = $_.DriveLetter
            path = $_.Path
            filesystem = $_.FileSystem
            health_status = $_.HealthStatus.ToString()
            operational_status = ($_.OperationalStatus -join ',')
            size = $_.Size
            size_remaining = $_.SizeRemaining
            percent_free = if ($_.Size -gt 0) { [math]::Round(($_.SizeRemaining / $_.Size) * 100, 2) } else { $null }
        }
    } | Write-JsonLine
}

Invoke-Section -Name 's2d_hci_physical_disks' -ScriptBlock {
    Get-PhysicalDisk | Sort-Object FriendlyName, SerialNumber | ForEach-Object {
        [pscustomobject]@{
            friendly_name = $_.FriendlyName
            serial_number = $_.SerialNumber
            manufacturer = $_.Manufacturer
            model = $_.Model
            firmware_version = $_.FirmwareVersion
            media_type = $_.MediaType.ToString()
            bus_type = $_.BusType.ToString()
            health_status = $_.HealthStatus.ToString()
            operational_status = ($_.OperationalStatus -join ',')
            usage = $_.Usage.ToString()
            can_pool = $_.CanPool
            size = $_.Size
            physical_location = $_.PhysicalLocation
            device_id = $_.DeviceId
            unique_id = $_.UniqueId
        }
    } | Write-JsonLine
}
