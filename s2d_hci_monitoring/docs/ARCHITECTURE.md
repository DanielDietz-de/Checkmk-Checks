# Architecture

## Goals

The design prioritizes deterministic service identity, explicit failure visibility, bounded collection, least privilege, and repeatable Checkmk deployment. It deliberately avoids a mutable coordinator or any action that changes Microsoft cluster state.

## Collection topology

Each physical cluster node runs the selected read-only collectors. Cluster-wide collectors call `Get-S2DHciClusterContext`, which selects the alphabetically first node currently reported `Up`. Only that elected node emits cluster/storage data. All nodes still emit their own collector-health record so failed election, missing modules, and standby state remain visible.

The elected node wraps cluster-wide sections in a Checkmk piggyback block named `s2d-cluster-<normalized-cluster-name>`. Because that name is independent of the current owner node, failover does not churn cluster monitoring identity.

Hyper-V collection is disabled by default. When enabled, each VM is emitted to `s2d-vm-<VM GUID>`, which keeps the monitoring host stable across live migration. Host-level VMMS health stays on the physical Hyper-V host.

## Versioned protocol

Every data row contains `protocol_version=1` and a UUID `run_id`. Server-side parsers reject unsupported versions and missing run IDs. Duplicate stable identities become explicit synthetic UNKNOWN services rather than overwriting earlier rows. Malformed JSON becomes a synthetic UNKNOWN parser service. Structured PowerShell section errors use `success=false` and are surfaced as UNKNOWN.

Every collector invocation ends with `s2d_hci_collector_health`, including success, complete/truncated flags, record/output/runtime accounting, collector role, logical host, cluster name, source host, and bounded errors.

## Bounds

The shared PowerShell module enforces three independent limits before emitting each record:

1. maximum wall-clock runtime;
2. maximum emitted data-record count;
3. maximum UTF-8 data bytes.

Default limits are 120 seconds, 2000 records, and 1 MiB. JSON configuration accepts only bounded integers and explicit Boolean values.

Checkmk Agent Bakery also supplies a Windows plug-in timeout, providing a second process-level boundary for direct collection. gMSA spool mode uses Task Scheduler `ExecutionTimeLimit` and `MultipleInstances IgnoreNew`.

## Stable identity

Storage objects use Microsoft stable IDs where available. Raw identifiers that may expose serials or paths are hashed before becoming service identity. Volumes use drive letters where present or a hashed stable identifier, with the filesystem label retained as display data. VM host identity uses the VM GUID. Per-VM objects use checkpoint IDs, NIC IDs, or controller coordinates.

## Failure isolation

Each Windows section executes independently through `Write-S2DHciSection`. A cmdlet error in one section does not stop later independent sections. The collector health envelope records that the overall run was incomplete. `Get-StorageHealthReport` is additionally isolated per storage subsystem.

The virtualization spool wrapper publishes only after validating exit code, JSON framing, protocol version, one consistent run ID, exactly one virtualization health envelope, and successful/complete/non-truncated status.
