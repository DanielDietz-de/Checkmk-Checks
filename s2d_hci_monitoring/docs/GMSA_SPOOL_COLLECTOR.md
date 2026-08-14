# gMSA virtualization spool collector

Use spool mode only when Hyper-V read access should run under a dedicated group Managed Service Account rather than the Checkmk agent identity.

## Prerequisites

- gMSA installed on the host and testable with `Test-ADServiceAccount`;
- Checkmk Windows agent directories present;
- Bakery `virtualization_mode = gmsa_spool` selected, or the required collector/wrapper binaries manually placed in the agent `bin` directory;
- `virtualization_enabled=true` in `config/s2d_hci.json`;
- direct virtualization plug-in deployment disabled for the same node.

## Install

1. In the Bakery rule select **Custom Hyper-V workload collection > Dedicated gMSA spool task** (`virtualization_mode = gmsa_spool`). This deploys the collector, wrapper, shared module, and shared `s2d_hci.json` configuration but intentionally does not invent or register a service-account identity.
2. Bake and deploy the Windows agent package. Confirm that direct Hyper-V plug-in mode is not selected for the same node.
3. Run `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1 -ServiceAccount 'DOMAIN\account$'`. Use `-DryRun` first to inspect the derived paths. `-WhatIf` is also side-effect free: directory creation, configuration writes, every ACL grant/verification, and task registration are all gated through PowerShell `ShouldProcess`. The installer requires the collector, wrapper, `bin/s2d_hci_common.psm1`, and `config/s2d_hci.json` to be present; writes only a non-secret spool path configuration; grants explicit read/execute or read rights to those runtime dependencies; grants read/execute traversal on the agent root, `bin`, and `config` directories; grants modify rights only to the spool directory; verifies the resulting NTFS rights; and registers a non-elevated scheduled task.
4. Run `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` and require `GmsaUsable`, all three traversal indicators, collector/wrapper/common-module read/execute indicators, both configuration-read indicators, and `SpoolModifyPresent` to be true before enabling production monitoring.

### Schedule and spool lifetime

The default spool filename is derived from `IntervalMinutes`. The installer keeps a minimum lifetime of 600 seconds and otherwise uses **two complete task intervals**. For example, the default five-minute task uses `600_s2d_hci_virtualization.txt`, while a 15-minute interval uses `1800_s2d_hci_virtualization.txt`. This prevents Checkmk from expiring valid data before the next scheduled collection and leaves one additional interval of tolerance for a delayed or missed run.

If `-SpoolFile` is supplied explicitly, its filename must begin with a numeric Checkmk lifetime prefix such as `1800_`, and that lifetime must cover at least two configured task intervals. The installer rejects an incompatible custom lifetime rather than creating a predictable monitoring gap.

## Runtime safety

The wrapper rejects paths outside the agent root and existing reparse points along trusted paths. It runs `powershell.exe -NoProfile -NonInteractive` without execution-policy bypass, requires a zero native exit code, validates protocol version and a single run ID, recomputes JSON data-record count and bytes and requires them to equal collector-health accounting, independently bounds Checkmk/piggyback framing and the bounded health envelope, and requires a successful complete collector-health result. Only then does it write a temporary file and atomically replace the live spool.

The previous spool remains untouched on every failure. The interval-derived numeric spool prefix provides Checkmk stale-data expiry independently of scheduled-task success without expiring before a valid schedule can refresh it.

Hyper-V pass-through disks are represented explicitly as `attachment_type=pass_through`; because they have no VHD path, the collector does not call `Get-VHD` for those attachments and does not create a false VHD metadata warning.

## Validation

Run `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` for the configured gMSA and confirm every reported runtime-access indicator plus `GmsaUsable`. Trigger the task manually, check Task Scheduler result, inspect the spool for one successful virtualization health envelope, and validate resulting VM piggyback hosts. For non-default task intervals, also confirm that the installed spool filename reports the derived lifetime expected from the schedule.
