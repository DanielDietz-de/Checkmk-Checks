# gMSA spool collector

## When to use it

Use the spool design when the normal Checkmk Windows agent service identity should not receive Hyper-V read permissions. A dedicated group Managed Service Account runs only the workload collector and writes its output to the Checkmk spool directory, where the normal agent reads it as data.

Do not run direct and spool-based virtualization collection at the same time.

## Security model

The gMSA should receive only:

- permission to log on as a scheduled task through normal domain and local policy;
- the minimum local Hyper-V read access required by the Microsoft cmdlets;
- read and execute access to the collector and wrapper;
- read access to the non-secret JSON configuration;
- create and replace access in the Checkmk spool directory.

It does not require a stored password. The installer accepts only account names ending in `$` and registers the task with the `ServiceAccount` logon type.

Do not make the gMSA a domain administrator, cluster administrator, local administrator, or unrestricted Hyper-V administrator solely for monitoring. Establish the narrowest workable rights in a test environment and record them in the organization’s access-control documentation.

## Files

| Source | Target on Windows |
| --- | --- |
| `src/agents/plugins/s2d_hci_virtualization.ps1` | `C:\ProgramData\checkmk\agent\plugins\s2d_hci_virtualization.ps1` |
| `src/agents/scripts/s2d_hci_virtualization_spool.ps1` | `C:\ProgramData\checkmk\agent\scripts\s2d_hci_virtualization_spool.ps1` |
| `src/agents/config/s2d_hci_virtualization.json` | `C:\ProgramData\checkmk\agent\config\s2d_hci_virtualization.json` |
| `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1` | temporary administrative location |
| `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` | temporary validation location |

The default spool output is:

```text
C:\ProgramData\checkmk\agent\spool\600_s2d_hci_virtualization.txt
```

The `600_` prefix tells Checkmk to stop using output after its stale lifetime. Keep this bounded so a failed task cannot make obsolete workload state appear current indefinitely.

## Installation

Copy the package files to the paths above, then preview the task definition from an elevated administrative PowerShell session:

```powershell
.\Install-S2DHciVirtualizationCollectorTask.ps1 `
  -ServiceAccount 'EXAMPLE\gmsa-cmk-s2d$' `
  -IntervalMinutes 5 `
  -DryRun

.\Install-S2DHciVirtualizationCollectorTask.ps1 `
  -ServiceAccount 'EXAMPLE\gmsa-cmk-s2d$' `
  -IntervalMinutes 5 `
  -WhatIf
```

After reviewing paths, identity, interval, and planned writes, apply the task:

```powershell
.\Install-S2DHciVirtualizationCollectorTask.ps1 `
  -ServiceAccount 'EXAMPLE\gmsa-cmk-s2d$' `
  -IntervalMinutes 5
```

The installer writes only the path configuration and scheduled-task definition. It never accepts or stores a password.

## Identity validation

The validation script must execute under the gMSA, not merely under an administrator account. Configure a one-time diagnostic action or temporarily point the scheduled task to the validation script, capture the JSON result, then restore the collector action.

```powershell
.\Test-S2DHciVirtualizationCollectorIdentity.ps1
```

Required successful checks:

- effective identity is the intended gMSA;
- `Get-VM` is available and readable;
- integration service, network adapter, and virtual disk probes succeed;
- replication probe succeeds when replication is in scope;
- a temporary file can be created and deleted in the spool directory.

An empty cluster or host may return no objects while the read probe still succeeds. A missing optional replication cmdlet should be reviewed against scope rather than solved with excessive permissions.

## Operational validation

```powershell
Get-ScheduledTask -TaskName 'Checkmk S2D HCI Virtualization Collector'
Get-ScheduledTaskInfo -TaskName 'Checkmk S2D HCI Virtualization Collector'
Get-Item 'C:\ProgramData\checkmk\agent\spool\600_s2d_hci_virtualization.txt'
Get-Content 'C:\ProgramData\checkmk\agent\spool\600_s2d_hci_virtualization.txt' -TotalCount 20
```

Verify the file is refreshed at the configured interval and contains complete `s2d_hci_virtualization_*` sections. Then confirm the same sections appear in normal Checkmk agent output.

## Failure handling

The wrapper writes a temporary file in the spool directory and replaces the live file only after collection completes. A failed collector therefore leaves the previous file in place until its numeric stale lifetime expires. Check the scheduled-task result and spool timestamp whenever Checkmk reports missing or stale workload data.

The wrapper rejects collector or spool paths outside the Checkmk agent roots while `require_paths_under_agent_root` is enabled. Do not disable this protection to work around ACL or deployment errors.

## Removal

1. Disable and remove the scheduled task.
2. Remove the wrapper, JSON configuration, and spool output.
3. Remove the virtualization collector if it is not used directly.
4. Remove the gMSA’s local rights and filesystem ACL entries.
5. Remove or retire the gMSA only after confirming it has no other consumers.
6. Rediscover the Checkmk host and remove vanished workload services under change control.
