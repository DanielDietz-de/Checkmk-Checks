#requires -Version 5.1
<#
.SYNOPSIS
    Validates the effective identity and read access required by the collector.

.DESCRIPTION
    Run this script through the scheduled task identity to prove that the gMSA can
    read local Hyper-V monitoring data and write to the configured Checkmk spool
    directory. The script does not modify Hyper-V, cluster, storage, service,
    registry, or firewall configuration.
#>

[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $env:ProgramData 'checkmk\agent\config\s2d_hci_virtualization.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

function New-ValidationResult {
    param(
        [Parameter(Mandatory)] [string]$Check,
        [Parameter(Mandatory)] [bool]$Success,
        [string]$Detail = ''
    )
    [pscustomobject]@{ check = $Check; success = $Success; detail = $Detail }
}

function Test-CommandReadAccess {
    param(
        [Parameter(Mandatory)] [string]$CommandName,
        [scriptblock]$Probe
    )
    if (-not (Get-Command -Name $CommandName -ErrorAction SilentlyContinue)) {
        return New-ValidationResult -Check $CommandName -Success $false -Detail 'Command not available.'
    }
    try {
        if ($Probe) { & $Probe | Out-Null }
        return New-ValidationResult -Check $CommandName -Success $true -Detail 'Read probe succeeded.'
    }
    catch {
        return New-ValidationResult -Check $CommandName -Success $false -Detail $_.Exception.Message
    }
}

$config = $null
if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
    try {
        $config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        New-ValidationResult -Check 'Configuration' -Success $false -Detail $_.Exception.Message
        exit 2
    }
}

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$results = @()
$results += New-ValidationResult -Check 'EffectiveIdentity' -Success $true -Detail $identity.Name
$results += Test-CommandReadAccess -CommandName 'Get-VM' -Probe { Get-VM -ErrorAction Stop | Select-Object -First 1 }
$results += Test-CommandReadAccess -CommandName 'Get-VMIntegrationService' -Probe { Get-VM -ErrorAction Stop | Select-Object -First 1 | ForEach-Object { Get-VMIntegrationService -VMName $_.Name -ErrorAction Stop | Select-Object -First 1 } }
$results += Test-CommandReadAccess -CommandName 'Get-VMNetworkAdapter' -Probe { Get-VM -ErrorAction Stop | Select-Object -First 1 | ForEach-Object { Get-VMNetworkAdapter -VMName $_.Name -ErrorAction Stop | Select-Object -First 1 } }
$results += Test-CommandReadAccess -CommandName 'Get-VMHardDiskDrive' -Probe { Get-VM -ErrorAction Stop | Select-Object -First 1 | ForEach-Object { Get-VMHardDiskDrive -VMName $_.Name -ErrorAction Stop | Select-Object -First 1 } }
$results += Test-CommandReadAccess -CommandName 'Get-VMReplication' -Probe { Get-VMReplication -ErrorAction Stop | Select-Object -First 1 }

if ($config -and $config.PSObject.Properties.Name -contains 'spool_file') {
    $probeFile = $null
    try {
        $spoolFile = [string]$config.spool_file
        $spoolDir = Split-Path -Parent $spoolFile
        $probeFile = Join-Path $spoolDir ('.s2d_hci_identity_probe_' + $PID + '.tmp')
        [System.IO.File]::WriteAllText($probeFile, 'probe', [System.Text.Encoding]::UTF8)
        [System.IO.File]::Delete($probeFile)
        $results += New-ValidationResult -Check 'SpoolWriteAccess' -Success $true -Detail $spoolDir
    }
    catch {
        if ($probeFile -and [System.IO.File]::Exists($probeFile)) {
            [System.IO.File]::Delete($probeFile)
        }
        $results += New-ValidationResult -Check 'SpoolWriteAccess' -Success $false -Detail $_.Exception.Message
    }
}
else {
    $results += New-ValidationResult -Check 'SpoolWriteAccess' -Success $false -Detail 'No spool_file configured.'
}

$results | ConvertTo-Json -Depth 5
if ($results | Where-Object { -not $_.success }) {
    exit 2
}
exit 0
