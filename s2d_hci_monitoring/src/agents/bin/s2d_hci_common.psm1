#requires -Version 5.1
<#
.SYNOPSIS
    Shared safety and protocol helpers for S2D/HCI Windows collectors.

.DESCRIPTION
    Provides bounded JSON emission, strict configuration parsing, deterministic
    cluster-leader election, piggyback framing, and collector-health reporting.
    The module performs no infrastructure mutation.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:S2DHciProtocolVersion = 1
$script:S2DHciMaximumHealthErrors = 20

# Handle convertto s2dhciboolean for this source file's runtime workflow.
function ConvertTo-S2DHciBoolean {
    <#
    .SYNOPSIS
        Convert a supported configuration value into a strict Boolean.
    .DESCRIPTION
        Accepts only actual Boolean values or explicit true/false text and
        rejects ambiguous values instead of relying on PowerShell truthiness.
    #>
    param(
        [Parameter(Mandatory)] [object]$Value,
        [Parameter(Mandatory)] [string]$Name
    )

    if ($Value -is [bool]) { return [bool]$Value }
    $text = [string]$Value
    if ($text.Trim().ToLowerInvariant() -eq 'true') { return $true }
    if ($text.Trim().ToLowerInvariant() -eq 'false') { return $false }
    throw "Configuration value '$Name' must be a Boolean."
}

# Handle convertto s2dhciboundedint for this source file's runtime workflow.
function ConvertTo-S2DHciBoundedInt {
    <#
    .SYNOPSIS
        Convert and validate one bounded integer configuration value.
    .DESCRIPTION
        Parses the supplied value as a 32-bit integer and rejects values
        outside the declared inclusive range.
    #>
    param(
        [Parameter(Mandatory)] [object]$Value,
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [int]$Minimum,
        [Parameter(Mandatory)] [int]$Maximum
    )

    $parsed = 0
    if (-not [int]::TryParse([string]$Value, [ref]$parsed)) { throw "Configuration value '$Name' must be an integer." }
    if ($parsed -lt $Minimum -or $parsed -gt $Maximum) { throw "Configuration value '$Name' must be between $Minimum and $Maximum." }
    return $parsed
}

# Handle get s2dhciagentroot for this source file's runtime workflow.
function Get-S2DHciAgentRoot {
    <#
    .SYNOPSIS
        Resolve the Checkmk agent root from a collector plug-in directory.
    .DESCRIPTION
        Treats the parent of the plug-in directory as the Checkmk agent root,
        matching the standard Windows agent layout.
    #>
    param([Parameter(Mandatory)] [string]$PluginRoot)

    return [System.IO.Path]::GetFullPath((Split-Path -Parent $PluginRoot))
}

# Handle get s2dhciconfig for this source file's runtime workflow.
function Get-S2DHciConfig {
    <#
    .SYNOPSIS
        Load and validate the non-secret S2D/HCI collector configuration.
    .DESCRIPTION
        Starts from conservative production defaults, optionally overlays the
        JSON configuration file, and validates every accepted setting. Invalid
        configuration falls back atomically to conservative defaults while an
        explicit error marker is carried into collector-health telemetry.
    #>
    param([Parameter(Mandatory)] [string]$AgentRoot)

    $defaults = [ordered]@{
        protocol_version = $script:S2DHciProtocolVersion
        max_records = 2000
        max_output_bytes = 1048576
        max_runtime_seconds = 120
        include_addresses = $false
        include_paths = $false
        include_serials = $false
        include_locations = $false
        virtualization_enabled = $false
    }
    $path = Join-Path $AgentRoot 'config\s2d_hci.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return [pscustomobject]$defaults }

    $resolved = [ordered]@{}
    foreach ($entry in $defaults.GetEnumerator()) { $resolved[$entry.Key] = $entry.Value }
    try {
        $json = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($json.PSObject.Properties.Name -contains 'protocol_version') {
            $resolved.protocol_version = ConvertTo-S2DHciBoundedInt -Value $json.protocol_version -Name 'protocol_version' -Minimum 1 -Maximum 1
        }
        if ($json.PSObject.Properties.Name -contains 'max_records') {
            $resolved.max_records = ConvertTo-S2DHciBoundedInt -Value $json.max_records -Name 'max_records' -Minimum 1 -Maximum 5000
        }
        if ($json.PSObject.Properties.Name -contains 'max_output_bytes') {
            $resolved.max_output_bytes = ConvertTo-S2DHciBoundedInt -Value $json.max_output_bytes -Name 'max_output_bytes' -Minimum 16384 -Maximum 4194304
        }
        if ($json.PSObject.Properties.Name -contains 'max_runtime_seconds') {
            $resolved.max_runtime_seconds = ConvertTo-S2DHciBoundedInt -Value $json.max_runtime_seconds -Name 'max_runtime_seconds' -Minimum 5 -Maximum 240
        }
        foreach ($name in @('include_addresses', 'include_paths', 'include_serials', 'include_locations', 'virtualization_enabled')) {
            if ($json.PSObject.Properties.Name -contains $name) { $resolved[$name] = ConvertTo-S2DHciBoolean -Value $json.$name -Name $name }
        }
    }
    catch {
        $defaults['configuration_error'] = 'Collector configuration is invalid; safe defaults are active.'
        return [pscustomobject]$defaults
    }
    return [pscustomobject]$resolved
}

# Handle new s2dhciruncontext for this source file's runtime workflow.
function New-S2DHciRunContext {
    <#
    .SYNOPSIS
        Create the mutable accounting state for one collector invocation.
    .DESCRIPTION
        Records the run identifier, output counters, bounded error list, role,
        and stopwatch used to build the final collector-health envelope. A shared
        configuration error is imported immediately so the run cannot appear OK.
    #>
    param(
        [Parameter(Mandatory)] [string]$Collector,
        [Parameter(Mandatory)] [object]$Config
    )

    $errorMessages = New-Object 'System.Collections.Generic.List[string]'
    $complete = $true
    $configurationError = $Config.PSObject.Properties['configuration_error']
    if ($null -ne $configurationError -and -not [string]::IsNullOrWhiteSpace([string]$configurationError.Value)) {
        $errorMessages.Add([string]$configurationError.Value)
        $complete = $false
    }
    return [pscustomobject]@{
        Collector = $Collector
        RunId = [guid]::NewGuid().Guid
        Config = $Config
        RecordCount = 0
        OutputBytes = 0
        ErrorMessages = $errorMessages
        ErrorsOmitted = 0
        Truncated = $false
        Complete = $complete
        Role = 'local'
        ClusterName = $null
        LogicalHost = $null
        Started = [DateTime]::UtcNow
        Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    }
}

# Handle add s2dhcicollectorerror for this source file's runtime workflow.
function Add-S2DHciCollectorError {
    <#
    .SYNOPSIS
        Record one bounded collector error and mark the run incomplete.
    .DESCRIPTION
        Retains at most twenty sanitized messages and counts additional errors
        without retaining their text. This bounds collector-health memory and
        output even when many independent objects fail in one invocation.
    #>
    param(
        [Parameter(Mandatory)] [object]$Context,
        [Parameter(Mandatory)] [string]$Message
    )

    $bounded = $Message.Trim()
    if ($bounded.Length -gt 512) { $bounded = $bounded.Substring(0, 512) + ' [truncated]' }
    if ($Context.ErrorMessages.Count -lt $script:S2DHciMaximumHealthErrors) { $Context.ErrorMessages.Add($bounded) }
    else { $Context.ErrorsOmitted++ }
    $Context.Complete = $false
}

# Handle add s2dhciprotocolfields for this source file's runtime workflow.
function Add-S2DHciProtocolFields {
    <#
    .SYNOPSIS
        Add protocol version and run identifier fields to one output object.
    .DESCRIPTION
        Copies public properties into an ordered object and injects the
        protocol metadata required to detect partial or mixed collector runs.
    #>
    param(
        [Parameter(Mandatory)] [object]$InputObject,
        [Parameter(Mandatory)] [object]$Context
    )

    $ordered = [ordered]@{ protocol_version = $script:S2DHciProtocolVersion; run_id = $Context.RunId }
    foreach ($property in $InputObject.PSObject.Properties) { $ordered[$property.Name] = $property.Value }
    return [pscustomobject]$ordered
}

# Handle write s2dhcijsonline for this source file's runtime workflow.
function Write-S2DHciJsonLine {
    <#
    .SYNOPSIS
        Serialize one record while enforcing record-count and byte limits.
    .DESCRIPTION
        Adds protocol metadata, serializes compact JSON, checks configured
        bounds before emitting output, and updates the run accounting state.
    #>
    param(
        [Parameter(Mandatory)] [object]$InputObject,
        [Parameter(Mandatory)] [object]$Context
    )

    if ($Context.Stopwatch.Elapsed.TotalSeconds -gt $Context.Config.max_runtime_seconds) {
        $Context.Truncated = $true; $Context.Complete = $false
        throw "Collector runtime limit of $($Context.Config.max_runtime_seconds) seconds was reached."
    }
    if ($Context.RecordCount -ge $Context.Config.max_records) {
        $Context.Truncated = $true; $Context.Complete = $false
        throw "Collector record limit of $($Context.Config.max_records) was reached."
    }
    $record = Add-S2DHciProtocolFields -InputObject $InputObject -Context $Context
    $line = $record | ConvertTo-Json -Compress -Depth 8
    $bytes = [System.Text.Encoding]::UTF8.GetByteCount($line) + 1
    if (($Context.OutputBytes + $bytes) -gt $Context.Config.max_output_bytes) {
        $Context.Truncated = $true; $Context.Complete = $false
        throw "Collector output limit of $($Context.Config.max_output_bytes) bytes was reached."
    }
    $Context.RecordCount++
    $Context.OutputBytes += $bytes
    Write-Output $line
}

# Handle write s2dhcisection for this source file's runtime workflow.
function Write-S2DHciSection {
    <#
    .SYNOPSIS
        Stream already-produced collector records through bounded JSON emission.
    .DESCRIPTION
        Emits one Checkmk section header and accepts records from the PowerShell
        pipeline. Records are serialized as they arrive, so record, byte, and
        elapsed-time bounds are enforced without buffering an entire cmdlet result.
        The Windows agent process timeout remains the hard deadline for a blocked
        upstream vendor cmdlet that produces no pipeline records.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [object]$Context,
        [Parameter(ValueFromPipeline = $true)] [AllowNull()] [object]$InputObject
    )

    begin { Write-Output "<<<$Name>>>" }
    process { if ($null -ne $InputObject) { Write-S2DHciJsonLine -InputObject $InputObject -Context $Context } }
}

# Handle write s2dhcisectionerror for this source file's runtime workflow.
function Write-S2DHciSectionError {
    <#
    .SYNOPSIS
        Convert one independently caught section failure into bounded telemetry.
    .DESCRIPTION
        Records the failure in collector health and attempts to emit a structured
        error object in the affected section. Both health and structured error text
        are bounded; if record capacity is exhausted, health remains authoritative.
    #>
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [object]$Context,
        [Parameter(Mandatory)] [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $errorMessage = ([string]$ErrorRecord.Exception.Message).Trim()
    if ($errorMessage.Length -gt 512) { $errorMessage = $errorMessage.Substring(0, 512) + ' [truncated]' }
    Add-S2DHciCollectorError -Context $Context -Message "${Name}: $errorMessage"
    try {
        [pscustomobject]@{ section = $Name; success = $false; error = $errorMessage } |
            Write-S2DHciSection -Name $Name -Context $Context
    }
    catch { }
}

# Handle convertto s2dhcihostname for this source file's runtime workflow.
function ConvertTo-S2DHciHostName {
    <#
    .SYNOPSIS
        Convert an arbitrary source name into a conservative piggyback host name.
    .DESCRIPTION
        Lowercases the name, replaces unsupported characters with hyphens, and
        removes leading or trailing separators while preserving deterministic identity.
    #>
    param([Parameter(Mandatory)] [string]$Value)

    $normalized = ($Value.ToLowerInvariant() -replace '[^a-z0-9_.-]', '-')
    $normalized = ($normalized -replace '-+', '-').Trim('-', '.')
    if ([string]::IsNullOrWhiteSpace($normalized)) { throw 'Cannot derive an empty piggyback host name.' }
    return $normalized
}

# Handle get s2dhcistablehash for this source file's runtime workflow.
function Get-S2DHciStableHash {
    <#
    .SYNOPSIS
        Return a short deterministic SHA-256 identifier for a sensitive value.
    .DESCRIPTION
        Hashes a stable source identifier and returns the first 16 hexadecimal
        characters so service identities remain deterministic without exposing raw values.
    #>
    param([Parameter(Mandatory)] [string]$Value)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        $digest = $sha.ComputeHash($bytes)
        return (($digest | ForEach-Object { $_.ToString('x2') }) -join '').Substring(0, 16)
    }
    finally { $sha.Dispose() }
}

# Handle get s2dhciclustercontext for this source file's runtime workflow.
function Get-S2DHciClusterContext {
    <#
    .SYNOPSIS
        Determine cluster identity, deterministic leader, and logical host name.
    .DESCRIPTION
        Elects the alphabetically first currently-Up cluster node. Every node
        computes the same result, so only one emits cluster-wide sections.
    #>
    param([Parameter(Mandatory)] [object]$Context)

    $cluster = Get-Cluster -ErrorAction Stop
    $upNodes = @(Get-ClusterNode -ErrorAction Stop | Where-Object { $_.State.ToString().ToLowerInvariant() -eq 'up' } | Sort-Object Name)
    if ($upNodes.Count -eq 0) { throw 'No Up cluster node is available for collector election.' }
    $current = $env:COMPUTERNAME.Split('.')[0]
    $leader = [string]$upNodes[0].Name
    $logicalHost = ConvertTo-S2DHciHostName -Value ("s2d-cluster-" + [string]$cluster.Name)
    $Context.ClusterName = [string]$cluster.Name
    $Context.LogicalHost = $logicalHost
    $Context.Role = if ($current.Equals($leader.Split('.')[0], [System.StringComparison]::OrdinalIgnoreCase)) { 'leader' } else { 'standby' }
    return [pscustomobject]@{ ClusterName=[string]$cluster.Name; Leader=$leader; CurrentNode=$current; LogicalHost=$logicalHost; IsLeader=($Context.Role -eq 'leader') }
}

# Handle start s2dhcipiggyback for this source file's runtime workflow.
function Start-S2DHciPiggyback {
    <#
    .SYNOPSIS
        Begin a Checkmk piggyback block for one logical host.
    .DESCRIPTION
        Emits the canonical opening marker used by Checkmk to attribute the following sections.
    #>
    param([Parameter(Mandatory)] [string]$HostName)
    Write-Output "<<<<$HostName>>>>"
}

# Handle stop s2dhcipiggyback for this source file's runtime workflow.
function Stop-S2DHciPiggyback {
    <#
    .SYNOPSIS
        Close the active Checkmk piggyback block.
    .DESCRIPTION
        Emits the canonical empty-host marker so subsequent health output belongs to the source node.
    #>
    param()
    Write-Output '<<<<>>>>'
}

# Handle write s2dhcicollectorhealth for this source file's runtime workflow.
function Write-S2DHciCollectorHealth {
    <#
    .SYNOPSIS
        Emit the final explicit collector-health service record.
    .DESCRIPTION
        Closes run accounting and exposes protocol version, role, bounds,
        bounded errors, omitted-error count, and completion state.
    #>
    param([Parameter(Mandatory)] [object]$Context)

    $Context.Stopwatch.Stop()
    Write-Output '<<<s2d_hci_collector_health>>>'
    $health = [ordered]@{
        protocol_version = $script:S2DHciProtocolVersion
        run_id = $Context.RunId
        collector = $Context.Collector
        success = ($Context.ErrorMessages.Count -eq 0 -and $Context.ErrorsOmitted -eq 0 -and -not $Context.Truncated)
        complete = [bool]$Context.Complete
        truncated = [bool]$Context.Truncated
        record_count = [int]$Context.RecordCount
        output_bytes = [int]$Context.OutputBytes
        max_records = [int]$Context.Config.max_records
        max_output_bytes = [int]$Context.Config.max_output_bytes
        max_runtime_seconds = [int]$Context.Config.max_runtime_seconds
        elapsed_ms = [int64]$Context.Stopwatch.ElapsedMilliseconds
        role = $Context.Role
        cluster_name = $Context.ClusterName
        logical_host = $Context.LogicalHost
        errors = @($Context.ErrorMessages)
        errors_omitted = [int]$Context.ErrorsOmitted
        started_utc = $Context.Started.ToString('o')
        finished_utc = [DateTime]::UtcNow.ToString('o')
    }
    Write-Output ($health | ConvertTo-Json -Compress -Depth 8)
}

Export-ModuleMember -Function @(
    'Get-S2DHciAgentRoot','Get-S2DHciConfig','New-S2DHciRunContext','Add-S2DHciCollectorError',
    'Write-S2DHciJsonLine','Write-S2DHciSection','Write-S2DHciSectionError','Get-S2DHciStableHash',
    'Get-S2DHciClusterContext','Start-S2DHciPiggyback','Stop-S2DHciPiggyback','Write-S2DHciCollectorHealth'
)
