# gMSA virtualization spool collector

Use spool mode only when Hyper-V read access should run under a dedicated group Managed Service Account rather than the Checkmk agent identity.

## Prerequisites

- gMSA installed on the host and testable with `Test-ADServiceAccount`;
- Checkmk Windows agent directories present;
- Bakery `gmsa_spool_support` enabled or the required binaries manually placed in the agent `bin` directory;
- `virtualization_enabled=true` in `config/s2d_hci.json`;
- direct virtualization plug-in deployment disabled for the same node.

## Install

Run `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1 -ServiceAccount 'DOMAIN\account$'`. Use `-DryRun` first to inspect derived paths. The installer writes only a non-secret path configuration, grants scoped ACLs, validates those ACLs, and registers a non-elevated scheduled task.

## Runtime safety

The wrapper rejects paths outside the agent root and existing reparse points along trusted paths. It runs `powershell.exe -NoProfile -NonInteractive` without execution-policy bypass, requires a zero native exit code, validates protocol version/run ID/collector-health completeness, writes to a temporary file, then atomically replaces the live spool.

The previous spool remains untouched on every failure. The numeric spool prefix provides Checkmk stale-data expiry independently of scheduled-task success.

## Validation

Run `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` for the configured gMSA and confirm all expected ACL indicators plus `GmsaUsable`. Trigger the task manually, check Task Scheduler result, inspect the spool for one successful virtualization health envelope, and validate resulting VM piggyback hosts.
