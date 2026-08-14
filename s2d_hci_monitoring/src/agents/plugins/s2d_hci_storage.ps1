#requires -Version 5.1
<#
.SYNOPSIS
    Bounded storage-state collector for S2D/HCI monitoring.
.DESCRIPTION
    Runs on the elected cluster node and emits stable, privacy-minimized storage
    records to the logical cluster piggyback host. The collector is read-only.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$pluginRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $pluginRoot))
if ((Split-Path -Leaf $agentRoot) -ieq 'plugins') {
    $agentRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $agentRoot))
}
Import-Module (Join-Path $agentRoot 'bin\s2d_hci_common.psm1') -Force -ErrorAction Stop
$configError = $null
try {
    $config = Get-S2DHciConfig -AgentRoot $agentRoot
}
catch {
    $configError = 'Collector configuration is invalid; safe defaults are active.'
    $config = [pscustomobject]@{
        protocol_version = 1
        max_records = 2000
        max_output_bytes = 1048576
        max_runtime_seconds = 120
        include_addresses = $false
        include_paths = $false
        include_serials = $false
        include_locations = $false
        virtualization_enabled = $false
    }
}
$context = New-S2DHciRunContext -Collector 'storage' -Config $config
if ($configError) {
    Add-S2DHciCollectorError -Context $context -Message $configError
}
$piggybackOpen = $false

try {
    Import-Module FailoverClusters -ErrorAction Stop
    Import-Module Storage -ErrorAction Stop
    $clusterContext = Get-S2DHciClusterContext -Context $context
    if ($clusterContext.IsLeader) {
        Start-S2DHciPiggyback -HostName $clusterContext.LogicalHost
        $piggybackOpen = $true

        $sectionName = 's2d_hci_csv'
        try {
            Get-ClusterSharedVolume -ErrorAction Stop | Sort-Object Name | ForEach-Object {
                $csv = $_
                foreach ($info in $csv.SharedVolumeInfo) {
                    $partition = $info.Partition
                    $identitySource = if ($csv.Id) { [string]$csv.Id } else { [string]$csv.Name }
                    $record = [ordered]@{
                        identity = "csv-$(Get-S2DHciStableHash -Value $identitySource)"
                        name = [string]$csv.Name
                        owner_node = [string]$csv.OwnerNode.Name
                        state = $csv.State.ToString()
                        filesystem = [string]$partition.FileSystem
                        size = $partition.Size
                        free_space = $partition.FreeSpace
                        percent_free = if ($partition.Size -gt 0) { [math]::Round(($partition.FreeSpace / $partition.Size) * 100, 2) } else { $null }
                    }
                    if ($config.include_paths) { $record.friendly_volume_name = [string]$info.FriendlyVolumeName }
                    [pscustomobject]$record
                }
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }

        $sectionName = 's2d_hci_storage_pools'
        try {
            Get-StoragePool -ErrorAction Stop | Where-Object { -not $_.IsPrimordial } | Sort-Object FriendlyName | ForEach-Object {
                $source = if ($_.UniqueId) { [string]$_.UniqueId } elseif ($_.ObjectId) { [string]$_.ObjectId } else { [string]$_.FriendlyName }
                [pscustomobject]@{
                    identity = "pool-$(Get-S2DHciStableHash -Value $source)"
                    friendly_name = [string]$_.FriendlyName
                    health_status = $_.HealthStatus.ToString()
                    operational_status = ($_.OperationalStatus -join ',')
                    size = $_.Size
                    allocated_size = $_.AllocatedSize
                    usage = $_.Usage.ToString()
                    is_read_only = $_.IsReadOnly
                    is_clustered = $_.IsClustered
                }
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }

        $sectionName = 's2d_hci_virtual_disks'
        try {
            Get-VirtualDisk -ErrorAction Stop | Sort-Object FriendlyName | ForEach-Object {
                $source = if ($_.UniqueId) { [string]$_.UniqueId } elseif ($_.ObjectId) { [string]$_.ObjectId } else { [string]$_.FriendlyName }
                [pscustomobject]@{
                    identity = "vdisk-$(Get-S2DHciStableHash -Value $source)"
                    friendly_name = [string]$_.FriendlyName
                    health_status = $_.HealthStatus.ToString()
                    operational_status = ($_.OperationalStatus -join ',')
                    detached_reason = [string]$_.DetachedReason
                    size = $_.Size
                    allocated_size = $_.AllocatedSize
                    footprint_on_pool = $_.FootprintOnPool
                    resiliency_setting_name = [string]$_.ResiliencySettingName
                    provisioning_type = $_.ProvisioningType.ToString()
                    physical_disk_redundancy = $_.PhysicalDiskRedundancy
                }
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }

        $sectionName = 's2d_hci_volumes'
        try {
            Get-Volume -ErrorAction Stop | Sort-Object FileSystemLabel, DriveLetter | ForEach-Object {
                $drive = if ($_.DriveLetter) { "$($_.DriveLetter):" } else { $null }
                $stableSource = if ($drive) { $drive } elseif ($_.UniqueId) { [string]$_.UniqueId } else { [string]$_.ObjectId }
                $locator = if ($drive) { $drive } else { "vol-$(Get-S2DHciStableHash -Value $stableSource)" }
                $label = [string]$_.FileSystemLabel
                $record = [ordered]@{
                    identity = $locator
                    filesystem_label = $label
                    drive_letter = $drive
                    filesystem = [string]$_.FileSystem
                    health_status = $_.HealthStatus.ToString()
                    operational_status = ($_.OperationalStatus -join ',')
                    size = $_.Size
                    size_remaining = $_.SizeRemaining
                    percent_free = if ($_.Size -gt 0) { [math]::Round(($_.SizeRemaining / $_.Size) * 100, 2) } else { $null }
                }
                if ($config.include_paths) { $record.path = [string]$_.Path }
                [pscustomobject]$record
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }

        $sectionName = 's2d_hci_physical_disks'
        try {
            Get-PhysicalDisk -ErrorAction Stop | Sort-Object FriendlyName, DeviceId | ForEach-Object {
                $stableSource = if ($_.UniqueId) { [string]$_.UniqueId } elseif ($_.SerialNumber) { [string]$_.SerialNumber } else { "$($_.FriendlyName)|$($_.DeviceId)" }
                $record = [ordered]@{
                    identity = "disk-$(Get-S2DHciStableHash -Value $stableSource)"
                    friendly_name = [string]$_.FriendlyName
                    manufacturer = [string]$_.Manufacturer
                    model = [string]$_.Model
                    firmware_version = [string]$_.FirmwareVersion
                    media_type = $_.MediaType.ToString()
                    bus_type = $_.BusType.ToString()
                    health_status = $_.HealthStatus.ToString()
                    operational_status = ($_.OperationalStatus -join ',')
                    usage = $_.Usage.ToString()
                    can_pool = $_.CanPool
                    size = $_.Size
                    device_id = [string]$_.DeviceId
                }
                if ($config.include_serials) {
                    $record.serial_number = [string]$_.SerialNumber
                    $record.unique_id = [string]$_.UniqueId
                }
                if ($config.include_locations) { $record.physical_location = [string]$_.PhysicalLocation }
                [pscustomobject]$record
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }
    }
}
catch {
    Add-S2DHciCollectorError -Context $context -Message "storage startup: $($_.Exception.Message)"
}
finally {
    if ($piggybackOpen) { Stop-S2DHciPiggyback }
    Write-S2DHciCollectorHealth -Context $context
}
