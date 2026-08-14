#requires -Version 5.1
<#
.SYNOPSIS
    Opt-in bounded Hyper-V workload collector for S2D/HCI monitoring.
.DESCRIPTION
    Emits host state locally and per-VM telemetry to stable VM-GUID piggyback
    hosts. Sensitive addresses and paths are omitted unless explicitly enabled.
    The collector is read-only and disabled by default. Once a configured data
    bound truncates a run, no additional VM framing is emitted.
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
$context = New-S2DHciRunContext -Collector 'virtualization' -Config $config

function Test-S2DHciCommandAvailable {
    <#
    .SYNOPSIS
        Test whether an optional Hyper-V command is available on the host.
    .DESCRIPTION
        Performs a non-throwing command lookup and returns a Boolean so optional
        features such as replication can be reported as unavailable rather than
        terminating the complete virtualization collector.
    #>
    param([Parameter(Mandatory)] [string]$Name)

    return $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Get-S2DHciVmPiggybackHost {
    <#
    .SYNOPSIS
        Derive the stable Checkmk piggyback host name for one virtual machine.
    .DESCRIPTION
        Prefixes the immutable VM GUID with the package namespace and applies
        conservative hostname normalization. The resulting identity remains the
        same when the VM live-migrates between Hyper-V cluster nodes.
    #>
    param([Parameter(Mandatory)] [guid]$VmId)

    return ConvertTo-S2DHciHostName -Value ("s2d-vm-" + $VmId.Guid)
}

function Write-S2DHciVmSections {
    <#
    .SYNOPSIS
        Emit all enabled monitoring sections for one VM on its stable piggyback host.
    .DESCRIPTION
        Opens the VM-GUID piggyback block, streams workload, integration,
        replication, checkpoint, NIC, and disk records through bounded section
        writers, and converts independent query failures into explicit telemetry.
        If a record or byte bound truncates the run, the function stops before
        emitting any further section or VM framing; a truncation exception does
        not trigger a second error-section header.
    #>
    param(
        [Parameter(Mandatory)] [object]$Vm,
        [Parameter(Mandatory)] [object]$RunContext,
        [Parameter(Mandatory)] [object]$CollectorConfig
    )

    if ($RunContext.Truncated) { return }

    $vmHost = Get-S2DHciVmPiggybackHost -VmId $Vm.VMId
    Start-S2DHciPiggyback -HostName $vmHost
    try {
        $sectionName = 's2d_hci_virtualization_workloads'
        try {
            $record = [ordered]@{
                name = [string]$Vm.Name
                vm_id = $Vm.VMId.Guid
                source_host = $env:COMPUTERNAME
                state = $Vm.State.ToString()
                status = [string]$Vm.Status
                generation = $Vm.Generation
                uptime_seconds = [int64]$Vm.Uptime.TotalSeconds
                cpu_usage = $Vm.CPUUsage
                memory_assigned = $Vm.MemoryAssigned
                memory_demand = $Vm.MemoryDemand
                memory_status = [string]$Vm.MemoryStatus
                dynamic_memory_enabled = $Vm.DynamicMemoryEnabled
                processor_count = $Vm.ProcessorCount
                configuration_version = $Vm.ConfigurationVersion.ToString()
            }
            if ($CollectorConfig.include_paths) { $record.path = [string]$Vm.Path }
            [pscustomobject]$record | Write-S2DHciSection -Name $sectionName -Context $RunContext
        }
        catch {
            if (-not $RunContext.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $RunContext -ErrorRecord $_ }
        }
        if ($RunContext.Truncated) { return }

        $sectionName = 's2d_hci_virtualization_services'
        try {
            Get-VMIntegrationService -VM $Vm -ErrorAction Stop | Sort-Object Name | ForEach-Object {
                [pscustomobject]@{
                    name = [string]$_.Name
                    enabled = $_.Enabled
                    primary_status_description = [string]$_.PrimaryStatusDescription
                    secondary_status_description = [string]$_.SecondaryStatusDescription
                }
            } | Write-S2DHciSection -Name $sectionName -Context $RunContext
        }
        catch {
            if (-not $RunContext.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $RunContext -ErrorRecord $_ }
        }
        if ($RunContext.Truncated) { return }

        $sectionName = 's2d_hci_virtualization_replication'
        try {
            if (-not (Test-S2DHciCommandAvailable -Name 'Get-VMReplication')) {
                [pscustomobject]@{ name='replication'; available=$false; reason='Get-VMReplication is unavailable.' } |
                    Write-S2DHciSection -Name $sectionName -Context $RunContext
            }
            else {
                Get-VMReplication -VMName $Vm.Name -ErrorAction Stop | ForEach-Object {
                    $record = [ordered]@{
                        name = 'replication'
                        state = $_.State.ToString()
                        health = $_.Health.ToString()
                        mode = $_.Mode.ToString()
                        frequency_sec = $_.FrequencySec
                        last_replication_time = $_.LastReplicationTime
                    }
                    if ($CollectorConfig.include_addresses) {
                        $record.primary_server = [string]$_.PrimaryServer
                        $record.replica_server = [string]$_.ReplicaServer
                    }
                    [pscustomobject]$record
                } | Write-S2DHciSection -Name $sectionName -Context $RunContext
            }
        }
        catch {
            if (-not $RunContext.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $RunContext -ErrorRecord $_ }
        }
        if ($RunContext.Truncated) { return }

        $sectionName = 's2d_hci_virtualization_checkpoints'
        try {
            Get-VMSnapshot -VM $Vm -ErrorAction Stop | Sort-Object CreationTime | ForEach-Object {
                [pscustomobject]@{
                    identity = "checkpoint-$($_.Id.Guid)"
                    name = [string]$_.Name
                    checkpoint_type = $_.CheckpointType.ToString()
                    creation_time = $_.CreationTime.ToUniversalTime().ToString('o')
                }
            } | Write-S2DHciSection -Name $sectionName -Context $RunContext
        }
        catch {
            if (-not $RunContext.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $RunContext -ErrorRecord $_ }
        }
        if ($RunContext.Truncated) { return }

        $sectionName = 's2d_hci_virtualization_network_adapters'
        try {
            Get-VMNetworkAdapter -VM $Vm -ErrorAction Stop | Sort-Object Name | ForEach-Object {
                $record = [ordered]@{
                    identity = "nic-$($_.Id)"
                    name = [string]$_.Name
                    switch_name = [string]$_.SwitchName
                    connected = $_.Connected
                    status = [string]$_.Status
                }
                if ($CollectorConfig.include_addresses) {
                    $record.mac_address = [string]$_.MacAddress
                    $record.ip_addresses = ($_.IPAddresses -join ',')
                }
                [pscustomobject]$record
            } | Write-S2DHciSection -Name $sectionName -Context $RunContext
        }
        catch {
            if (-not $RunContext.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $RunContext -ErrorRecord $_ }
        }
        if ($RunContext.Truncated) { return }

        $sectionName = 's2d_hci_virtualization_hard_disks'
        try {
            Get-VMHardDiskDrive -VM $Vm -ErrorAction Stop | Sort-Object ControllerType, ControllerNumber, ControllerLocation | ForEach-Object {
                $drive = $_
                $drivePath = [string]$drive.Path
                $isPassThrough = [string]::IsNullOrWhiteSpace($drivePath) -and $null -ne $drive.DiskNumber
                $attachmentType = 'unknown'
                if ($isPassThrough) {
                    $attachmentType = 'pass_through'
                }
                elseif (-not [string]::IsNullOrWhiteSpace($drivePath)) {
                    $attachmentType = 'vhd'
                }
                $record = [ordered]@{
                    identity = "$($drive.ControllerType)$($drive.ControllerNumber):$($drive.ControllerLocation)"
                    controller_type = $drive.ControllerType.ToString()
                    controller_number = $drive.ControllerNumber
                    controller_location = $drive.ControllerLocation
                    disk_number = $drive.DiskNumber
                    attachment_type = $attachmentType
                }

                if (-not [string]::IsNullOrWhiteSpace($drivePath) -and (Test-S2DHciCommandAvailable -Name 'Get-VHD')) {
                    try {
                        $vhd = Get-VHD -Path $drivePath -ErrorAction Stop
                        $record.vhd_type = $vhd.VhdType.ToString()
                        $record.vhd_format = $vhd.VhdFormat.ToString()
                        $record.size = $vhd.Size
                        $record.file_size = $vhd.FileSize
                        $record.minimum_size = $vhd.MinimumSize
                        $record.has_parent = -not [string]::IsNullOrWhiteSpace([string]$vhd.ParentPath)
                        if ($CollectorConfig.include_paths) { $record.parent_path = [string]$vhd.ParentPath }
                    }
                    catch {
                        if ($CollectorConfig.include_paths) {
                            $errorMessage = [string]$_.Exception.Message
                            if ($errorMessage.Length -gt 512) { $errorMessage = $errorMessage.Substring(0, 512) + ' [truncated]' }
                            $record.vhd_error = $errorMessage
                        }
                        else { $record.vhd_error = 'VHD metadata query failed; path details are redacted by policy.' }
                    }
                }
                if ($CollectorConfig.include_paths -and -not [string]::IsNullOrWhiteSpace($drivePath)) { $record.path = $drivePath }
                [pscustomobject]$record
            } | Write-S2DHciSection -Name $sectionName -Context $RunContext
        }
        catch {
            if (-not $RunContext.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $RunContext -ErrorRecord $_ }
        }
    }
    finally { Stop-S2DHciPiggyback }
}

try {
    if (-not $config.virtualization_enabled) { $context.Role = 'disabled' }
    else {
        Import-Module Hyper-V -ErrorAction Stop
        $sectionName = 's2d_hci_virtualization_host'
        try {
            $service = Get-Service -Name 'vmms' -ErrorAction Stop
            [pscustomobject]@{
                name = $env:COMPUTERNAME
                service_status = $service.Status.ToString()
                service_start_type = $service.StartType.ToString()
                module_available = $true
            } | Write-S2DHciSection -Name $sectionName -Context $context
        }
        catch {
            if (-not $context.Truncated) { Write-S2DHciSectionError -Name $sectionName -Context $context -ErrorRecord $_ }
        }

        Get-VM -ErrorAction Stop | Sort-Object VMId | ForEach-Object {
            if (-not $context.Truncated) {
                Write-S2DHciVmSections -Vm $_ -RunContext $context -CollectorConfig $config
            }
        }
    }
}
catch { Add-S2DHciCollectorError -Context $context -Message "virtualization startup: $($_.Exception.Message)" }
finally { Write-S2DHciCollectorHealth -Context $context }
