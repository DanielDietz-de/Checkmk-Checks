#requires -Version 5.1
<#
.SYNOPSIS
    Run the opt-in Hyper-V collector and atomically maintain a validated spool file.
.DESCRIPTION
    Executes the collector under a dedicated scheduled-task identity, validates
    the versioned protocol and final collector-health envelope, and replaces the
    live spool file only after a complete successful run. The previous valid
    spool file is preserved on every failure.
#>

[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $env:ProgramData 'checkmk\agent\config\s2d_hci_virtualization_spool.json'),
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-S2DHciPathUnderRoot {
    <#
    .SYNOPSIS
        Verify that a normalized path remains strictly below a trusted root.
    .DESCRIPTION
        Resolves both paths to absolute form and performs an ordinal-ignore-case
        prefix check with a directory separator boundary. The function prevents
        configured spool or collector paths from escaping the intended agent tree.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-S2DHciNoReparsePoint {
    <#
    .SYNOPSIS
        Reject reparse points along a trusted collector or spool path.
    .DESCRIPTION
        Confirms root confinement, then walks each existing path component and
        fails closed when a junction, symlink, or other reparse point is found.
        This prevents path redirection after configuration validation.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-S2DHciPathUnderRoot -Path $fullPath -Root $fullRoot) -and -not $fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes trusted root '$fullRoot': $fullPath"
    }

    $relative = $fullPath.Substring($fullRoot.Length).TrimStart([System.IO.Path]::DirectorySeparatorChar)
    $cursor = $fullRoot
    foreach ($part in $relative.Split([System.IO.Path]::DirectorySeparatorChar, [System.StringSplitOptions]::RemoveEmptyEntries)) {
        $cursor = Join-Path $cursor $part
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Reparse points are not permitted in trusted collector paths: $cursor"
            }
        }
    }
}

function Read-S2DHciSpoolConfig {
    <#
    .SYNOPSIS
        Load and validate the non-secret virtualization spool configuration.
    .DESCRIPTION
        Reads the JSON file and requires explicit collector_path and spool_file
        values. Missing or blank fields terminate the run before any collector is
        launched, preserving the previously valid spool file.
    #>
    param([Parameter(Mandatory)] [string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Spool configuration not found: $Path"
    }
    $json = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($name in @('collector_path', 'spool_file')) {
        if (-not ($json.PSObject.Properties.Name -contains $name) -or [string]::IsNullOrWhiteSpace([string]$json.$name)) {
            throw "Spool configuration requires '$name'."
        }
    }
    return $json
}

function Test-S2DHciCollectorOutput {
    <#
    .SYNOPSIS
        Validate a complete virtualization collector run before spool publication.
    .DESCRIPTION
        Enforces the output-size bound, JSON framing, protocol version, single run
        identifier, exactly one matching collector-health envelope, and successful
        completion. Any violation throws so the existing live spool is preserved.
    #>
    param(
        [Parameter(Mandatory)] [string[]]$Lines,
        [Parameter(Mandatory)] [int]$MaximumBytes
    )

    $joined = $Lines -join [System.Environment]::NewLine
    $bytes = [System.Text.Encoding]::UTF8.GetByteCount($joined)
    if ($bytes -gt ($MaximumBytes + 32768)) {
        throw "Collector output exceeds the configured data bound plus protocol overhead."
    }

    $runId = $null
    $healthRows = New-Object 'System.Collections.Generic.List[object]'
    $inHealth = $false
    foreach ($line in $Lines) {
        $trimmed = ([string]$line).Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith('<<<<') -and $trimmed.EndsWith('>>>>')) { continue }
        if ($trimmed.StartsWith('<<<') -and $trimmed.EndsWith('>>>')) {
            $inHealth = ($trimmed -eq '<<<s2d_hci_collector_health>>>')
            continue
        }

        try { $record = $trimmed | ConvertFrom-Json -ErrorAction Stop }
        catch { throw "Collector emitted non-JSON data outside a section marker: $trimmed" }

        if (-not ($record.PSObject.Properties.Name -contains 'protocol_version') -or [int]$record.protocol_version -ne 1) {
            throw 'Collector output contains an unsupported or missing protocol version.'
        }
        if (-not ($record.PSObject.Properties.Name -contains 'run_id') -or [string]::IsNullOrWhiteSpace([string]$record.run_id)) {
            throw 'Collector output contains a record without a run identifier.'
        }
        if ($null -eq $runId) { $runId = [string]$record.run_id }
        elseif (-not $runId.Equals([string]$record.run_id, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'Collector output mixes multiple run identifiers.'
        }
        if ($inHealth) { $healthRows.Add($record) }
    }

    if ($healthRows.Count -ne 1) { throw "Expected exactly one collector-health row, found $($healthRows.Count)." }
    $health = $healthRows[0]
    if ([string]$health.collector -ne 'virtualization') { throw 'Collector-health row belongs to the wrong collector.' }
    if (-not [bool]$health.success -or -not [bool]$health.complete -or [bool]$health.truncated) {
        throw "Virtualization collector did not complete successfully: $($health.errors -join '; ')"
    }
    if ([string]$health.role -eq 'disabled') { throw 'Virtualization collection is disabled in s2d_hci.json.' }
    return $true
}

$AgentRoot = [System.IO.Path]::GetFullPath($AgentRoot)
$configRoot = Join-Path $AgentRoot 'config'
$binRoot = Join-Path $AgentRoot 'bin'
$spoolRoot = Join-Path $AgentRoot 'spool'

foreach ($trusted in @($ConfigPath, $configRoot, $binRoot, $spoolRoot)) {
    Assert-S2DHciNoReparsePoint -Path $trusted -Root $AgentRoot
}
$config = Read-S2DHciSpoolConfig -Path $ConfigPath
$collectorPath = [System.IO.Path]::GetFullPath([string]$config.collector_path)
$spoolFile = [System.IO.Path]::GetFullPath([string]$config.spool_file)
if (-not (Test-S2DHciPathUnderRoot -Path $collectorPath -Root $binRoot)) { throw "Collector must remain below '$binRoot'." }
if (-not (Test-S2DHciPathUnderRoot -Path $spoolFile -Root $spoolRoot)) { throw "Spool file must remain below '$spoolRoot'." }
Assert-S2DHciNoReparsePoint -Path $collectorPath -Root $AgentRoot
Assert-S2DHciNoReparsePoint -Path $spoolFile -Root $AgentRoot

if (-not (Test-Path -LiteralPath $collectorPath -PathType Leaf)) { throw "Collector script not found: $collectorPath" }
if (-not (Test-Path -LiteralPath $spoolRoot -PathType Container)) { throw "Checkmk spool directory not found: $spoolRoot" }

$collectorConfig = Join-Path $configRoot 's2d_hci.json'
$maximumBytes = 1048576
if (Test-Path -LiteralPath $collectorConfig -PathType Leaf) {
    $collectorJson = Get-Content -LiteralPath $collectorConfig -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($collectorJson.PSObject.Properties.Name -contains 'max_output_bytes') { $maximumBytes = [int]$collectorJson.max_output_bytes }
}

$output = @(& powershell.exe -NoProfile -NonInteractive -File $collectorPath 2>&1 | ForEach-Object { [string]$_ })
$collectorExitCode = $LASTEXITCODE
if ($collectorExitCode -ne 0) {
    $diagnostics = ($output -join [System.Environment]::NewLine).Trim()
    if ($diagnostics.Length -gt 4096) { $diagnostics = $diagnostics.Substring(0, 4096) + ' [truncated]' }
    throw "Collector exited with code $collectorExitCode; previous spool preserved. Diagnostics: $diagnostics"
}
$null = Test-S2DHciCollectorOutput -Lines $output -MaximumBytes $maximumBytes

$spoolDirectory = Split-Path -Parent $spoolFile
$tempFile = Join-Path $spoolDirectory ('.' + [System.IO.Path]::GetFileName($spoolFile) + ".$PID.tmp")
try {
    [System.IO.File]::WriteAllLines($tempFile, $output, (New-Object System.Text.UTF8Encoding($false)))
    if ([System.IO.File]::Exists($spoolFile)) { [System.IO.File]::Replace($tempFile, $spoolFile, $null) }
    else { [System.IO.File]::Move($tempFile, $spoolFile) }
}
finally {
    if ([System.IO.File]::Exists($tempFile)) { [System.IO.File]::Delete($tempFile) }
}
