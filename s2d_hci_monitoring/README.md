# s2d_hci_monitoring

Read-only, production-hardened monitoring for Microsoft Failover Clustering, Storage Spaces Direct (S2D), HCI storage, and optional Hyper-V workloads on Checkmk 2.5.

## What the package does

The package separates collection into bounded Windows PowerShell collectors and server-side Checkmk plug-ins. Cluster-wide collectors elect exactly one currently `Up` cluster node and send cluster data to a stable `s2d-cluster-<cluster>` piggyback host. Optional Hyper-V workload data is sent to stable `s2d-vm-<vm-guid>` piggyback hosts, so VM live migration does not change monitoring identity.

Every collector record uses **protocol version 1** and a per-run `run_id`. Every physical collector invocation emits `<<<s2d_hci_collector_health>>>`, including success/completion state, role, record count, byte count, elapsed time, configured limits, and bounded error messages. Malformed JSON, duplicate identities, protocol mismatches, structured collector failures, incomplete runs, and truncation are surfaced as UNKNOWN/CRIT monitoring instead of silently becoming empty discovery.

## Compatibility and prerequisites

- Checkmk: **2.5.0 through 2.5.99**.
- Windows PowerShell: **5.1 or newer**.
- Failover cluster collectors: `FailoverClusters` module.
- Storage collectors: `Storage` module.
- Hyper-V collector: `Hyper-V` module; custom workload collection is **disabled by default**.
- gMSA task installation: `ActiveDirectory` tooling providing `Test-ADServiceAccount`.

The collectors are read-only. They do not modify cluster, storage, Hyper-V, registry, firewall, service, or network configuration.

## Collectors and default intervals

| Collector | Scope | Default Bakery interval |
| --- | --- | ---: |
| `s2d_hci_fast.ps1` | cluster identity, quorum, nodes, networks, roles/resources | 120 s |
| `s2d_hci_storage.ps1` | CSVs, pools, virtual disks, volumes, physical disks | 300 s |
| `s2d_hci_jobs.ps1` | storage repair/resynchronization jobs | 300 s |
| `s2d_hci_health.ps1` | S2D state, storage subsystems, health reports | 600 s |
| `s2d_hci_virtualization.ps1` | optional Hyper-V host and VM telemetry | 300 s |

The former unbounded performance-history collector is intentionally **not packaged**.

## Agent Bakery deployment

Use **Setup > Agents > Windows, Linux, Solaris, AIX > Agent rules > S2D/HCI monitoring collectors** and apply the rule only to intended Windows cluster nodes. The four cluster/storage collectors can be enabled independently. `virtualization_mode` is deliberately a mutually exclusive choice so the same node cannot receive both direct and spool-based custom Hyper-V collection:

| `virtualization_mode` | Behavior |
| --- | --- |
| `disabled` | Default. Do not deploy the custom Hyper-V collector. |
| `direct` | Deploy `s2d_hci_virtualization.ps1` as a normal bounded Checkmk Windows agent plug-in. |
| `gmsa_spool` | Deploy the virtualization collector and fail-safe spool wrapper as support binaries for a separately registered gMSA scheduled task. |

The gMSA mode does **not** register a Windows Scheduled Task automatically because the service-account identity is host/environment specific. After baking the support files, use `tools/windows/Install-S2DHciVirtualizationCollectorTask.ps1` and validate the account/ACLs with `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1`.

Safe defaults are:

- `max_records`: 2000
- `max_output_bytes`: 1 MiB
- `max_runtime_seconds`: 120
- addresses: excluded
- filesystem/VHD paths: excluded
- physical-disk serials/unique IDs: excluded
- physical locations: excluded
- custom Hyper-V workload monitoring: disabled

The Bakery places the shared PowerShell module in the Windows agent `bin` directory and writes `config/s2d_hci.json`. Direct plug-ins receive an agent-level timeout in addition to their own internal limits.

## Manual deployment

Manual deployment is supported for controlled environments. Copy the files listed in `src/info` to the corresponding Checkmk Windows agent source locations. At minimum, direct plug-ins require `bin/s2d_hci_common.psm1` and `config/s2d_hci.json` in addition to the selected plug-in scripts. Prefer Agent Bakery for repeatable deployments.

For gMSA spool mode, follow [gMSA spool collector](docs/GMSA_SPOOL_COLLECTOR.md). Do not run direct and spool-based virtualization collection simultaneously.

## Thresholds and state policy

Rules are provided for:

- CSV free space: WARN below 15%, CRIT below 10%;
- volume free space: WARN below 15%, CRIT below 10%;
- VM CPU: WARN at 80%, CRIT at 95%;
- VM memory pressure: WARN at 100%, CRIT at 120%;
- retained checkpoint age: WARN at 24 h, CRIT at 72 h;
- operational-state mapping for degraded, paused, draining/resynchronizing, offline/failed, and unknown states.

Unknown or unrecognized vendor states default to **UNKNOWN**, not OK.

## Security model

Collectors enforce bounded runtime, record count, and output bytes. Sensitive fields are omitted by default. Stable identities use non-sensitive Microsoft IDs where available or short SHA-256-derived identifiers where raw IDs, paths, or serials should not be exposed.

The gMSA workflow validates the service account locally, confines all paths to the Checkmk agent root, rejects reparse-point escapes, grants scoped NTFS rights, uses `RunLevel Limited`, uses `MultipleInstances IgnoreNew`, avoids `ExecutionPolicy Bypass`, and replaces the spool atomically only after validating a complete successful protocol run. A failed run preserves the last valid spool file.

See [Security](docs/SECURITY.md) for the threat model and operational controls.

## Validation and production acceptance

Repository validation covers Python syntax, package tests, PowerShell contract checks, deterministic MKP creation, checksums, SPDX/provenance generation from repository release tooling, and clean Checkmk registration/runtime validation. The package also documents a production acceptance checklist for representative Windows Server/S2D/Hyper-V infrastructure.

Repository CI cannot truthfully substitute for environment-specific evidence such as real cluster cmdlet output, gMSA permissions, alert routing, live migration, and production runtime measurements. Record those results before production promotion.

See [Validation](docs/VALIDATION.md) and [Production acceptance](docs/PRODUCTION_ACCEPTANCE.md).

## Documentation index

- [Architecture](docs/ARCHITECTURE.md)
- [Code layout and implementation map](docs/CODE_LAYOUT.md)
- [Collector protocol](docs/PROTOCOL.md)
- [Installation and operations](docs/INSTALLATION_AND_OPERATIONS.md)
- [gMSA spool collector](docs/GMSA_SPOOL_COLLECTOR.md)
- [Security](docs/SECURITY.md)
- [Validation](docs/VALIDATION.md)
- [Production acceptance](docs/PRODUCTION_ACCEPTANCE.md)
- [Release and rollback](docs/RELEASE.md)
- [Upstream provenance](docs/UPSTREAM_PROVENANCE.md)

## Migration and license

The original migration baseline is `Daniel-Dietz/S2D-Monitoring` commit `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`. The production-hardening requirements were taken from source PR #8 and reimplemented directly in this repository because that PR's encoded materialization bundle was not reliable.

This package retains the [PolyForm Internal Use License 1.0.0](LICENSE).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `s2d_hci_monitoring` version `1.1.0`; minimum Checkmk version `2.5.0`; maximum asserted version: 2.5.99.
- Canonical manifest: `s2d_hci_monitoring/src/info`; it declares 21 packaged files.
- No committed MKP artifact is present; build and validate the package from `src/` before installation.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/s2d_hci/agent_based/s2d_hci_collector_health.py`, `src/s2d_hci/agent_based/s2d_hci_fast.py`, `src/s2d_hci/agent_based/s2d_hci_health.py`, `src/s2d_hci/agent_based/s2d_hci_jobs.py`, `src/s2d_hci/agent_based/s2d_hci_protocol.py`, `src/s2d_hci/agent_based/s2d_hci_storage.py`, `src/s2d_hci/agent_based/s2d_hci_virtualization.py`.
- **Rulesets:** `src/s2d_hci/rulesets/bakery.py`, `src/s2d_hci/rulesets/ruleset_s2d_hci.py`, `src/s2d_hci/rulesets/ruleset_s2d_hci_workloads.py`.
- **Graphing:** `src/s2d_hci/graphing/graphing_s2d_hci.py`.
- **Bakery:** `src/lib/python3/cmk/base/cee/plugins/bakery/s2d_hci.py`.
- **Check manuals:** `src/s2d_hci/checkman/s2d_hci`.
- **Other packaged source:** `src/agents/bin/s2d_hci_common.psm1`, `src/agents/config/s2d_hci.json`, `src/agents/plugins/s2d_hci_fast.ps1`, `src/agents/plugins/s2d_hci_health.ps1`, `src/agents/plugins/s2d_hci_jobs.ps1`, `src/agents/plugins/s2d_hci_storage.ps1`, `src/agents/plugins/s2d_hci_virtualization.ps1`, `src/agents/scripts/s2d_hci_virtualization_spool.ps1`.
- Registered check plug-in names: `s2d_hci_cluster_groups`, `s2d_hci_cluster_resources`, `s2d_hci_cluster_summary`, `s2d_hci_collector_health`, `s2d_hci_csv`, `s2d_hci_network_interfaces`, `s2d_hci_networks`, `s2d_hci_nodes`, `s2d_hci_physical_disks`, `s2d_hci_quorum`, `s2d_hci_s2d_state`, `s2d_hci_storage_health_report`, `s2d_hci_storage_jobs`, `s2d_hci_storage_pools`, `s2d_hci_storage_subsystems`, `s2d_hci_virtual_disks`, `s2d_hci_virtualization_checkpoints`, `s2d_hci_virtualization_hard_disks`, `s2d_hci_virtualization_host`, `s2d_hci_virtualization_network_adapters`, `s2d_hci_virtualization_replication`, `s2d_hci_virtualization_services`, `s2d_hci_virtualization_workloads`, `s2d_hci_volumes`.

### Validation

- Package-specific tests: `tests/test_bakery_contracts.py`, `tests/test_code_documentation.py`, `tests/test_collector_health.py`, `tests/test_graphing_contracts.py`, `tests/test_manifest_integrity.py`, `tests/test_powershell_contracts.py`, `tests/test_protocol.py`, `tests/test_s2d_hci_checks.py`, `tests/test_storage_scope_contracts.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `s2d_hci_collector_health`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
