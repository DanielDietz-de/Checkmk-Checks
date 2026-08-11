#requires -Version 5.1
<#
.SYNOPSIS
    Remove the S2D/HCI gMSA scheduled task and optional generated state.
.DESCRIPTION
    Removes only the named task and, when explicitly requested, the generated
    spool configuration and spool file. Packaged collector files are left to
    the Checkmk agent package lifecycle.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = 'Checkmk S2D HCI Virtualization Collector',
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent'),
    [switch]$RemoveGeneratedState
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Remove-S2DHciFileIfPresent {
    <#
    .SYNOPSIS
        Remove one explicitly selected generated collector state file when present.
    .DESCRIPTION
        Performs an idempotent literal-path check and removes only the file passed
        by the caller. Normal task removal leaves generated state untouched unless
        the operator explicitly requests the RemoveGeneratedState lifecycle step.
    #>
    param([Parameter(Mandatory)] [string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) { Remove-Item -LiteralPath $Path -Force }
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess($TaskName, 'Unregister scheduled task')) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }
}
if ($RemoveGeneratedState) {
    $root = [System.IO.Path]::GetFullPath($AgentRoot)
    foreach ($path in @(
        (Join-Path $root 'config\s2d_hci_virtualization_spool.json'),
        (Join-Path $root 'spool\600_s2d_hci_virtualization.txt')
    )) {
        if ($PSCmdlet.ShouldProcess($path, 'Remove generated state')) { Remove-S2DHciFileIfPresent -Path $path }
    }
}
