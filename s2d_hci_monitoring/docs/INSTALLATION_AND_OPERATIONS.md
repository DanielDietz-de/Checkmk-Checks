# Installation and operations

## Prerequisites

- Checkmk 2.5.x;
- Windows PowerShell 5.1 or newer on monitored nodes;
- `FailoverClusters` for cluster collectors;
- `Storage` for storage collectors;
- `Hyper-V` only when custom workload collection is enabled;
- enough agent runtime for the selected bounded collector timeout.

## Recommended deployment: Agent Bakery

Create the Agent Bakery rule **S2D/HCI monitoring collectors** and scope it only to intended Windows cluster nodes.

Cluster/storage collectors may be enabled independently. Custom Hyper-V collection is controlled by the mutually exclusive `virtualization_mode` setting:

- `disabled` — default; no custom Hyper-V collector;
- `direct` — normal Checkmk Windows agent plug-in;
- `gmsa_spool` — collector and fail-safe wrapper are delivered as support binaries for a separately registered gMSA task.

The Bakery deploys timed collectors using Checkmk's normal cached plug-in layout. Depending on the agent/runtime path, a collector can therefore execute from either `agent\plugins` or `agent\plugins\<interval>`. Every packaged collector normalizes both layouts back to the real Checkmk agent root before importing `bin\s2d_hci_common.psm1` or reading `config\s2d_hci.json`; interval caching must not change configuration or module resolution.

After baking and installing the agent, re-run service discovery on:

1. physical cluster nodes for collector-health and local host services;
2. the generated `s2d-cluster-<cluster>` piggyback host;
3. generated `s2d-vm-<VM GUID>` piggyback hosts only when custom Hyper-V collection is enabled.

## Manual deployment

For controlled/manual installations, copy the package files from `src/` to the corresponding Checkmk Windows agent paths. Direct plug-ins may execute from the normal `plugins` directory; the same bootstrap logic also supports Checkmk-created one-level cached interval directories below `plugins`.

At minimum, direct collectors require:

- the selected plug-in scripts;
- `bin/s2d_hci_common.psm1`;
- `config/s2d_hci.json`.

Prefer Bakery deployment so interval, timeout, privacy, and mode settings remain centrally reproducible.

## gMSA spool mode

The Bakery does not register a scheduled task because the gMSA identity is environment-specific. After support files are deployed, use `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1`, starting with `-DryRun`. Validate the account and runtime ACL contract with `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1`.

The task installer confines collector/wrapper paths to the agent `bin` tree, spool configuration to `config`, and output to `spool`. An existing task's registered `ConfigPath` is immutable for in-place updates; use the remove/reinstall lifecycle documented in [gMSA spool collector](GMSA_SPOOL_COLLECTOR.md) when that path must change.

Do not enable direct and gMSA-spool virtualization collection on the same node.

## Operational checks after deployment

- Confirm every physical collector reports one `S2D/HCI collector health` service.
- Confirm only the elected cluster node emits cluster-wide piggyback sections.
- Confirm healthy cluster/storage objects remain OK and failed or unavailable commands are visible as UNKNOWN/CRIT rather than disappearing.
- Confirm custom Hyper-V data appears only when explicitly enabled.
- Confirm sensitive addresses, paths, serials, and physical locations remain absent unless their corresponding settings are enabled.
- For gMSA mode, confirm the scheduled task result, the configured spool lifetime/path, runtime identity validation, and exactly one active package spool snapshot.

## Troubleshooting

If cluster-wide services disappear, inspect the physical collector-health service first. Startup/module/configuration failures are expected to surface there even when object sections cannot be collected.

If a Bakery-timed collector reports missing `plugins\bin\s2d_hci_common.psm1` or reads configuration below `plugins\config`, verify that the deployed script is from the current package: cached interval execution must normalize `plugins\<interval>` back to the agent root.

If gMSA spool data becomes stale, inspect Task Scheduler, run the identity validator, check the generated spool config, and verify that no superseded `*_s2d_hci_virtualization.txt` file remains after an interval/path update.
