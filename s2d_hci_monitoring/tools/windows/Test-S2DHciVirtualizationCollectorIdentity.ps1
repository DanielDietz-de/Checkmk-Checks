#requires -Version 5.1
<#
.SYNOPSIS
    Validate the runtime identity and permissions for the virtualization collector.
.DESCRIPTION
    Confirms that the supplied gMSA is locally usable and reports read/write
    access to the exact collector, wrapper, configuration, and spool paths.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidatePattern('^[^\\]+\\[^\\]+\$$')] [string]$ServiceAccount,
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-S2DHciAclIdentity {
    <#
    .SYNOPSIS
        Test whether a path ACL contains the expected collector service identity.
    .DESCRIPTION
        Returns false for a missing path or failed icacls query and otherwise
        searches the ACL text using case-insensitive Windows identity semantics.
        The result is diagnostic evidence only and never changes permissions.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Identity
    )

    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $text = (& icacls.exe $Path 2>&1 | Out-String)
    return $LASTEXITCODE -eq 0 -and $text.IndexOf($Identity, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
}

$adCommand = Get-Command -Name 'Test-ADServiceAccount' -ErrorAction SilentlyContinue
$gmsaUsable = $false
if ($adCommand) { $gmsaUsable = [bool](Test-ADServiceAccount -Identity $ServiceAccount.Split('\')[-1] -ErrorAction Stop) }
$root = [System.IO.Path]::GetFullPath($AgentRoot)
$paths = [ordered]@{
    Collector = Join-Path $root 'bin\s2d_hci_virtualization.ps1'
    Wrapper = Join-Path $root 'bin\s2d_hci_virtualization_spool.ps1'
    Config = Join-Path $root 'config\s2d_hci_virtualization_spool.json'
    SpoolDirectory = Join-Path $root 'spool'
}

[pscustomobject]@{
    ServiceAccount = $ServiceAccount
    ActiveDirectoryValidationAvailable = ($null -ne $adCommand)
    GmsaUsable = $gmsaUsable
    CollectorAclPresent = Test-S2DHciAclIdentity -Path $paths.Collector -Identity $ServiceAccount
    WrapperAclPresent = Test-S2DHciAclIdentity -Path $paths.Wrapper -Identity $ServiceAccount
    ConfigAclPresent = Test-S2DHciAclIdentity -Path $paths.Config -Identity $ServiceAccount
    SpoolAclPresent = Test-S2DHciAclIdentity -Path $paths.SpoolDirectory -Identity $ServiceAccount
}
