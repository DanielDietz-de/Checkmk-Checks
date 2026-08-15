#requires -Version 5.1
<#
.SYNOPSIS
    Validate the runtime identity and permissions for the virtualization collector.
.DESCRIPTION
    Confirms that the supplied gMSA is locally usable and verifies the concrete
    NTFS rights required for agent-root traversal, collector/wrapper/shared-module
    execution, collector/spool configuration reads, and spool-directory writes.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidatePattern('^[^\\]+\\[^\\]+\$$')] [string]$ServiceAccount,
    [string]$AgentRoot = (Join-Path $env:ProgramData 'checkmk\agent')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Handle test-s2dhciaclrights for this module's workflow.
function Test-S2DHciAclRights {
    <#
    .SYNOPSIS
        Test whether a path ACL grants the expected gMSA all required NTFS rights.
    .DESCRIPTION
        Resolves the service identity to its SID, reads the target ACL, and returns
        true only when an allow rule for that SID contains every requested
        FileSystemRights bit. Missing paths, unresolved identities, and ACL read
        failures return false; this diagnostic function never changes permissions.
    #>
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Identity,
        [Parameter(Mandatory)] [System.Security.AccessControl.FileSystemRights]$RequiredRights
    )

    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $targetSid = (New-Object System.Security.Principal.NTAccount($Identity)).Translate([System.Security.Principal.SecurityIdentifier])
        $acl = Get-Acl -LiteralPath $Path
        foreach ($rule in $acl.Access) {
            if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) { continue }
            try { $ruleSid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]) }
            catch { continue }
            if ($ruleSid.Value -ne $targetSid.Value) { continue }
            if (($rule.FileSystemRights -band $RequiredRights) -eq $RequiredRights) { return $true }
        }
    }
    catch { return $false }
    return $false
}

$adCommand = Get-Command -Name 'Test-ADServiceAccount' -ErrorAction SilentlyContinue
$gmsaUsable = $false
if ($adCommand) { $gmsaUsable = [bool](Test-ADServiceAccount -Identity $ServiceAccount.Split('\')[-1] -ErrorAction Stop) }
$root = [System.IO.Path]::GetFullPath($AgentRoot)
$paths = [ordered]@{
    AgentRoot = $root
    BinDirectory = Join-Path $root 'bin'
    ConfigDirectory = Join-Path $root 'config'
    Collector = Join-Path $root 'bin\s2d_hci_virtualization.ps1'
    Wrapper = Join-Path $root 'bin\s2d_hci_virtualization_spool.ps1'
    CommonModule = Join-Path $root 'bin\s2d_hci_common.psm1'
    CollectorConfig = Join-Path $root 'config\s2d_hci.json'
    SpoolConfig = Join-Path $root 'config\s2d_hci_virtualization_spool.json'
    SpoolDirectory = Join-Path $root 'spool'
}

[pscustomobject]@{
    ServiceAccount = $ServiceAccount
    ActiveDirectoryValidationAvailable = ($null -ne $adCommand)
    GmsaUsable = $gmsaUsable
    AgentRootTraversePresent = Test-S2DHciAclRights -Path $paths.AgentRoot -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::ReadAndExecute)
    BinTraversePresent = Test-S2DHciAclRights -Path $paths.BinDirectory -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::ReadAndExecute)
    ConfigTraversePresent = Test-S2DHciAclRights -Path $paths.ConfigDirectory -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::ReadAndExecute)
    CollectorReadExecutePresent = Test-S2DHciAclRights -Path $paths.Collector -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::ReadAndExecute)
    WrapperReadExecutePresent = Test-S2DHciAclRights -Path $paths.Wrapper -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::ReadAndExecute)
    CommonModuleReadExecutePresent = Test-S2DHciAclRights -Path $paths.CommonModule -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::ReadAndExecute)
    CollectorConfigReadPresent = Test-S2DHciAclRights -Path $paths.CollectorConfig -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::Read)
    SpoolConfigReadPresent = Test-S2DHciAclRights -Path $paths.SpoolConfig -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::Read)
    SpoolModifyPresent = Test-S2DHciAclRights -Path $paths.SpoolDirectory -Identity $ServiceAccount -RequiredRights ([System.Security.AccessControl.FileSystemRights]::Modify)
}
