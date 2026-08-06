#requires -Version 5.1
<#
.SYNOPSIS
    Writes workload collector output to a Checkmk spool file.

.DESCRIPTION
    This wrapper is intended to run from a Windows Scheduled Task under a dedicated gMSA.
    It reads non-secret settings from a JSON configuration file, executes the configured
    read-only collector script, and atomically replaces the configured spool file.

    Do not configure passwords in this file or in the JSON configuration file.
#>

[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $env:ProgramData 'checkmk\agent\config\s2d_hci_virtualization.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-DefaultConfig {
    $agentRoot = Join-Path $env:ProgramData 'checkmk\agent'
    [pscustomobject]@{
        collector_path = Join-Path $agentRoot 'plugins\s2d_hci_virtualization.ps1'
        spool_file = Join-Path $agentRoot 'spool\600_s2d_hci_virtualization.txt'
        require_paths_under_agent_root = $true
    }
}

function Read-CollectorConfig {
    param([Parameter(Mandatory)] [string]$Path)

    $config = Get-DefaultConfig
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $json = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($name in @('collector_path', 'spool_file', 'require_paths_under_agent_root')) {
            if ($json.PSObject.Properties.Name -contains $name) {
                $config.$name = $json.$name
            }
        }
    }
    return $config
}

function Test-PathUnderRoot {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

$config = Read-CollectorConfig -Path $ConfigPath
$agentRoot = Join-Path $env:ProgramData 'checkmk\agent'
$spoolRoot = Join-Path $agentRoot 'spool'
$collectorPath = [string]$config.collector_path
$spoolFile = [string]$config.spool_file

if ($config.require_paths_under_agent_root) {
    if (-not (Test-PathUnderRoot -Path $collectorPath -Root $agentRoot)) {
        throw "Collector path must remain below the Checkmk agent root: $collectorPath"
    }
    if (-not (Test-PathUnderRoot -Path $spoolFile -Root $spoolRoot)) {
        throw "Spool file must remain below the Checkmk spool root: $spoolFile"
    }
}

if (-not (Test-Path -LiteralPath $collectorPath -PathType Leaf)) {
    throw "Collector script not found: $collectorPath"
}
if (-not (Test-Path -LiteralPath $spoolRoot -PathType Container)) {
    throw "Checkmk spool directory not found: $spoolRoot"
}

$output = & powershell.exe -NoProfile -NonInteractive -File $collectorPath 2>&1
$spoolDirectory = Split-Path -Parent $spoolFile
$tempFile = Join-Path $spoolDirectory ('.' + [System.IO.Path]::GetFileName($spoolFile) + ".$PID.tmp")

try {
    [System.IO.File]::WriteAllLines($tempFile, [string[]]$output, [System.Text.Encoding]::UTF8)
    if ([System.IO.File]::Exists($spoolFile)) {
        [System.IO.File]::Replace($tempFile, $spoolFile, $null)
    }
    else {
        [System.IO.File]::Move($tempFile, $spoolFile)
    }
}
finally {
    if ([System.IO.File]::Exists($tempFile)) {
        [System.IO.File]::Delete($tempFile)
    }
}
