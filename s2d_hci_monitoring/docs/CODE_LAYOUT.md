# Code layout and implementation map

This document maps the production code to its runtime responsibility so a maintainer can locate behavior without reverse-engineering the package. `src/info` remains the canonical MKP ownership manifest; this map explains the purpose and data flow behind those files.

## Runtime flow

1. The Checkmk Windows agent executes one or more bounded collector scripts from `src/agents/plugins/`.
2. Every collector imports `src/agents/bin/s2d_hci_common.psm1` for configuration validation, hard limits, protocol framing, leader election, stable identities, piggyback framing, and collector-health output.
3. Cluster-wide collectors elect one currently `Up` cluster node. Only that node emits cluster-wide data, inside a stable `s2d-cluster-*` piggyback block.
4. Optional Hyper-V collection emits each VM into a stable `s2d-vm-<VM GUID>` piggyback block so live migration does not change monitoring identity.
5. Server-side modules in `src/s2d_hci/agent_based/` validate protocol version and run IDs, preserve malformed/duplicate/failed input as visible services, and evaluate the resulting Checkmk states.
6. Rulesets under `src/s2d_hci/rulesets/` provide deployment choices, state mapping, and thresholds. Graph definitions under `src/s2d_hci/graphing/` describe emitted performance metrics.

## Windows collection layer

| Path | Responsibility |
| --- | --- |
| `src/agents/bin/s2d_hci_common.psm1` | Shared safety/protocol library. Validates non-secret configuration, enforces runtime/record/output bounds, creates run context, elects the cluster collector, derives privacy-preserving identities, writes piggyback framing, and emits final collector health. |
| `src/agents/plugins/s2d_hci_fast.ps1` | Fast-changing failover-cluster state: cluster identity, quorum, nodes, networks/interfaces, clustered roles, and resources. Runs cluster-wide data only on the elected node. |
| `src/agents/plugins/s2d_hci_storage.ps1` | Storage inventory and capacity: CSVs, storage pools, virtual disks, volumes, and physical disks. Applies privacy settings before sensitive paths/serial/location data can leave the host. |
| `src/agents/plugins/s2d_hci_jobs.ps1` | Active Storage Spaces repair/resynchronization jobs and finite completion progress. |
| `src/agents/plugins/s2d_hci_health.ps1` | S2D state, storage subsystems, and storage-health reports. Normalizes Windows Server cmdlet/property variations into the stable package protocol. |
| `src/agents/plugins/s2d_hci_virtualization.ps1` | Optional Hyper-V host and VM telemetry. Disabled by default; VM data is grouped under stable VM-GUID piggyback hosts. |
| `src/agents/config/s2d_hci.json` | Non-secret collector defaults and hard safety/privacy limits written or overridden by Bakery. |
| `src/agents/scripts/s2d_hci_virtualization_spool.ps1` | Fail-safe gMSA spool publisher. Validates confined paths, reparse points, native exit status, protocol framing, one run ID, and a successful final health envelope before atomically replacing the live spool. |

## Checkmk server-side layer

| Path | Responsibility |
| --- | --- |
| `src/s2d_hci/agent_based/s2d_hci_protocol.py` | Shared defensive parser, finite numeric/Boolean conversion, collector-error extraction, synthetic protocol-error records, duplicate detection, and conservative Microsoft-state mapping. |
| `src/s2d_hci/agent_based/s2d_hci_collector_health.py` | Parses final collector-health envelopes and reports failed, incomplete, truncated, disabled, standby, malformed, or healthy runs explicitly. |
| `src/s2d_hci/agent_based/s2d_hci_fast.py` | Parsers/discovery/checks for cluster, quorum, node, network/interface, role, and resource state. |
| `src/s2d_hci/agent_based/s2d_hci_storage.py` | Parsers/discovery/checks for CSVs, storage pools, virtual disks, volumes, and physical disks; applies capacity thresholds and duplicate-safe identities. |
| `src/s2d_hci/agent_based/s2d_hci_jobs.py` | Storage-job state and finite progress metric handling. |
| `src/s2d_hci/agent_based/s2d_hci_health.py` | S2D and storage-health checks, including unsupported-command and per-object failure handling. |
| `src/s2d_hci/agent_based/s2d_hci_virtualization.py` | Optional Hyper-V host/workload/integration/replication/checkpoint/NIC/disk checks plus CPU, memory-pressure, and checkpoint-age thresholds. |
| `src/s2d_hci/rulesets/bakery.py` | User-facing Agent Bakery rule. Selects the four core collectors, mutually exclusive Hyper-V mode, hard limits, and sensitive-field opt-ins. |
| `src/lib/python3/cmk/base/cee/plugins/bakery/s2d_hci.py` | Server-side Bakery file generator. Converts rules into Windows `Plugin`, `SystemBinary`, and `PluginConfig` artifacts with bounded timeouts. |
| `src/s2d_hci/rulesets/ruleset_s2d_hci.py` | Shared operational-state mapping and CSV/volume free-space threshold forms. |
| `src/s2d_hci/rulesets/ruleset_s2d_hci_workloads.py` | VM CPU/memory-pressure and checkpoint-age forms, including all required shared state-policy defaults. |
| `src/s2d_hci/graphing/graphing_s2d_hci.py` | Checkmk Graphing API metric, graph, and perfometer definitions for all emitted performance values. |
| `src/s2d_hci/checkman/s2d_hci` | Operator-facing Checkmk check manual and section/troubleshooting reference. |

## gMSA lifecycle tools

| Path | Responsibility |
| --- | --- |
| `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1` | Validates the local gMSA, confines paths, writes non-secret spool configuration, applies/verifies scoped ACLs, and registers the non-elevated scheduled task. |
| `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1` | Read-only diagnostic for local gMSA usability and expected collector/wrapper/config/spool ACL presence. |
| `tools/windows/Remove-S2DHciVirtualizationCollectorTask.ps1` | Removes the named scheduled task and, only when explicitly requested, generated spool/config state. Packaged files remain under the Checkmk agent lifecycle. |

## Test map

| Test | Contract protected |
| --- | --- |
| `tests/test_code_documentation.py` | Human-readable Python module/function/class docs and PowerShell script/function `.SYNOPSIS`/`.DESCRIPTION` help. |
| `tests/test_protocol.py` | Protocol version/run ID handling, malformed rows, duplicates, finite conversion, and conservative parsing. |
| `tests/test_collector_health.py` | Explicit health service behavior for successful and failed/incomplete runs. |
| `tests/test_s2d_hci_checks.py` | Critical check behavior including quorum failures, duplicate volume identities, non-finite job progress, and ruleset/default compatibility. |
| `tests/test_powershell_contracts.py` | Static Windows safety contracts such as bounded/fail-safe collection, no execution-policy bypass, least privilege, and spool preservation. |
| `tests/test_bakery_contracts.py` | Bakery opt-in deployment modes, bounded configuration, and manifest-owned Windows artifacts. |
| `tests/test_graphing_contracts.py` | Checkmk 2.5 Graphing API object contracts and metric title types. |
| `tests/test_manifest_integrity.py` | Canonical MKP ownership/version metadata and removal of obsolete performance-history files. |

## Where to change behavior

- **Collector output or Microsoft cmdlets:** change the relevant `src/agents/plugins/*.ps1` collector and its focused PowerShell/protocol tests.
- **Shared protocol, bounds, leader election, privacy identity, or health envelope:** change `s2d_hci_common.psm1` and the corresponding Python protocol/health tests.
- **Parsing or service state:** change the relevant `src/s2d_hci/agent_based/*.py` module and add a focused fixture before updating documentation.
- **Thresholds or state mapping:** update both the check defaults and the matching ruleset form; Checkmk 2.5 validates these contracts together.
- **Deployment files or modes:** update both `src/s2d_hci/rulesets/bakery.py` and `src/lib/python3/cmk/base/cee/plugins/bakery/s2d_hci.py`, then update `src/info` only if package ownership changes.
- **gMSA permissions/task behavior:** change the lifecycle tools and spool wrapper together, preserving least privilege and last-good-spool semantics.

Any behavioral change must keep code, focused tests, `src/info`, README/runbooks, and generated repository reference material synchronized before merge.
