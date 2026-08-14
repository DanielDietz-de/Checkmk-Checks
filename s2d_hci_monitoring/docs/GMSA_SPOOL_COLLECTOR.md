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
3. Run `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1 -ServiceAccount 'DOMAIN\account$'`. Use `-DryRun` first to inspect the derived paths. `-WhatIf` is also side-effect free: task quiescing, directory creation, configuration writes, generated-state cleanup, every ACL grant/verification, and task registration are all gated through PowerShell `ShouldProcess`. The installer requires the collector, wrapper, `bin/s2d_hci_common.psm1`, and `config/s2d_hci.json` to be present; writes only a non-secret spool path configuration; grants explicit read/execute or read rights to those runtime dependencies; grants read/execute traversal on the agent root, `bin`, and `config` directories; grants modify rights only to the spool directory; verifies the resulting NTFS rights; and registers a non-elevated scheduled task.
4. Run `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` and require `GmsaUsable`, all three traversal indicators, collector/wrapper/common-module read/execute indicators, both configuration-read indicators, and `SpoolModifyPresent` to be true before enabling production monitoring.

### Schedule and spool lifetime

The default spool filename is derived from `IntervalMinutes`. The installer keeps a minimum lifetime of 600 seconds and otherwise uses **two complete task intervals**. For example, the default five-minute task uses `600_s2d_hci_virtualization.txt`, while a 15-minute interval uses `1800_s2d_hci_virtualization.txt`. This prevents Checkmk from expiring valid data before the next scheduled collection and leaves one additional interval of tolerance for a delayed or missed run.

If `-SpoolFile` is supplied explicitly, its filename must begin with a numeric Checkmk lifetime prefix such as `1800_`, and that lifetime must cover at least two configured task intervals. The installer rejects an incompatible custom lifetime rather than creating a predictable monitoring gap.

When an update changes the configured spool filename—most commonly because `IntervalMinutes` changes—the installer reads the previous generated configuration **before replacing it**, confines the previous `spool_file` to the trusted spool directory, and then quiesces the existing root task before any generated-state mutation. Quiescing first disables the task so no new trigger can start, stops all running task instances, and verifies a bounded transition out of the running state. Only after that point does the installer remove the old snapshot and any stale file already present at the new target path. This prevents an in-flight old wrapper from recreating the retired spool after cleanup and causing mixed-run ingestion.

The generated spool configuration path itself is an installation identity boundary. Before updating an existing root scheduled task, the installer enumerates every registered `-ConfigPath` occurrence across all task actions and requires **exactly one**. That path must remain below the trusted Checkmk `config` directory, exist, and match the requested `-ConfigPath`. Missing, duplicate, ambiguous, or untrusted arguments fail closed. An in-place `ConfigPath` change is rejected; remove the task with generated state and reinstall it at the new path instead. This prevents an old configuration and its spool snapshot from remaining active after task lifecycle changes.

The update path is intentionally fail-closed. After state and ACL validation, the replacement task definition is registered with disabled settings first. Only after registration succeeds does the installer explicitly enable the root task. Therefore an error during final enablement cannot leave a newly registered publisher running despite the installer reporting failure. If an earlier error occurs after an existing task was quiesced, the old task remains disabled rather than resuming publication against partially changed state. Correct the reported error and rerun the installer.

## Runtime safety

The wrapper rejects paths outside the agent root and existing reparse points along trusted paths. It runs `powershell.exe -NoProfile -NonInteractive` without execution-policy bypass, requires a zero native exit code, validates protocol version and a single run ID, recomputes JSON data-record count and bytes and requires them to equal collector-health accounting, independently bounds Checkmk/piggyback framing and the bounded health envelope, and requires a successful complete collector-health result. Only then does it write a temporary file and atomically replace the live spool.

The previous spool remains untouched on a normal collector/runtime failure. Configuration lifecycle changes are different: when the operator intentionally changes the spool path, the installer first prevents the old task from publishing again and then retires the old generated snapshot so only one package snapshot remains active. The interval-derived numeric spool prefix provides Checkmk stale-data expiry independently of scheduled-task success without expiring before a valid schedule can refresh it.

In direct Hyper-V mode, once a configured data bound marks the run truncated, no additional VM section headers, piggyback openings, or error-section retries are emitted. The current already-open piggyback block is closed and the final collector-health envelope reports the truncated run.

Hyper-V pass-through disks are represented explicitly as `attachment_type=pass_through`; because they have no VHD path, the collector does not call `Get-VHD` for those attachments and does not create a false VHD metadata warning.

## Removal

`Remove-S2DHciVirtualizationCollectorTask.ps1` discovers all required state before changing the live task. With `-RemoveGeneratedState`, it enumerates the task's registered `-ConfigPath` arguments and requires exactly one when the task exists, confines that path to the trusted config directory, requires any explicitly supplied `-ConfigPath` to match it, reads the generated configuration to recover the custom/derived spool path, and enumerates package-standard `^\d+_s2d_hci_virtualization\.txt$` snapshots. Missing, duplicate, ambiguous, mismatched, or unsafe registered state therefore leaves the live task untouched for operator inspection.

After discovery succeeds, removal quiesces an existing root task before unregistering it: the task is disabled to prevent new triggers, all running instances are stopped, and a bounded exit from the running state is required. Only then is the task unregistered. When `-RemoveGeneratedState` is present, the validated snapshots and configuration are deleted after unregistering. This ordering prevents a wrapper that had already loaded its configuration from recreating supposedly removed spool state. If quiescing or unregistering fails, the task/state deletion sequence stops fail-closed. The removal path honors `ShouldProcess`/`-WhatIf` and never deletes a configured spool path outside the trusted Checkmk spool directory.

## Validation

Run `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` for the configured gMSA and confirm every reported runtime-access indicator plus `GmsaUsable`. Trigger the task manually, check Task Scheduler result, inspect the spool for one successful virtualization health envelope, and validate resulting VM piggyback hosts. For non-default task intervals, also confirm that the installed spool filename reports the derived lifetime expected from the schedule and that no superseded `*_s2d_hci_virtualization.txt` snapshot remains.
