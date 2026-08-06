# s2d_hci_monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.5.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0p9-blue) ![usable until](https://img.shields.io/badge/usable%20until-2.5.99-green)
<!-- compatibility-badges:end -->

Read-only monitoring for Microsoft Windows Failover Clustering, Storage Spaces Direct, HCI storage, and Hyper-V workloads. The package uses split Windows collectors plus Checkmk Check API V2, Rulesets API V1, and Graphing API V1 components.

## Scope and compatibility

- Checkmk 2.5.0 through 2.5.99; Checkmk 2.4 and Check API V1 are not supported.
- Windows PowerShell 5.1 or newer.
- `FailoverClusters`, `Storage`, and `Hyper-V` modules where the corresponding collector is deployed.
- Local read access to the monitored Microsoft management cmdlets.
- Optional virtualization spool mode under a dedicated gMSA with only the required Hyper-V read access and Checkmk spool write access.

The package monitors cluster identity, quorum, nodes, networks, resources, CSVs, pools, disks, volumes, storage jobs, S2D health, optional performance history, Hyper-V host state, workloads, integration services, replication, checkpoints, virtual NICs, and virtual disks. It does not alter cluster, storage, Hyper-V, service, registry, network, or firewall state.

## Collector design

| Collector | Recommended interval |
| --- | ---: |
| `s2d_hci_fast.ps1` | 60–120 seconds |
| `s2d_hci_storage.ps1` | 300 seconds |
| `s2d_hci_jobs.ps1` | 300 seconds |
| `s2d_hci_health.ps1` | 600 seconds |
| `s2d_hci_perf.ps1` | 900 seconds |
| `s2d_hci_virtualization.ps1` | 120–300 seconds |

Collectors emit compact JSON lines below `s2d_hci_*` agent sections. Malformed individual rows are ignored without suppressing valid rows from the same section. Expensive collectors must use Checkmk caching or the documented spool workflow; do not add sleeps to the scripts.

See [Architecture](docs/ARCHITECTURE.md) and [gMSA spool collector](docs/GMSA_SPOOL_COLLECTOR.md).

## Installation

1. Obtain the MKP and matching SHA-256 file produced by a successful repository validation run.
2. Verify it with `sha256sum --check s2d_hci_monitoring-1.0.0.mkp.sha256`.
3. Install and enable it through Checkmk Setup or the `mkp` command supported by the installed 2.5 release.
4. Deploy only the applicable Windows collectors through the normal controlled agent process.
5. Run `cmk-validate-plugins`, inspect raw `s2d_hci_*` sections, rediscover services on a test host, and verify representative OK, WARN, CRIT, and UNKNOWN states.

The MKP provides the agent files but does not currently implement Agent Bakery deployment. Detailed installation, upgrade, rollback, removal, and troubleshooting procedures are in [Installation and operations](docs/INSTALLATION_AND_OPERATIONS.md).

## Thresholds

Rules are provided for CSV and volume free-space levels, workload CPU and memory pressure, and retained checkpoint age. Defaults are:

- free space: WARN below 15%, CRIT below 10%;
- workload CPU: WARN at 80%, CRIT at 95%;
- memory pressure: WARN at 100%, CRIT at 120%;
- checkpoint age: WARN at 24 hours, CRIT at 72 hours.

Apply rules narrowly to intended cluster nodes and items.

## Security and failure behavior

All packaged collectors are intended to remain read-only. Do not grant broad administrative roles where narrower read access is sufficient. The gMSA task path stores no password, uses the Scheduled Tasks `ServiceAccount` logon type, confines configured paths to the Checkmk agent root, and atomically replaces the spool file without an execution-policy bypass.

Known unhealthy or offline states map conservatively to WARN or CRIT. Unknown vendor values, unavailable optional cmdlets, malformed data, and missing expected telemetry map to UNKNOWN rather than a false healthy state. The numeric spool-file prefix bounds stale-data lifetime.

Raw agent output can contain infrastructure-sensitive names, addresses, serial numbers, paths, and topology. Sanitize diagnostics before public disclosure. See [Security](docs/SECURITY.md).

## Validation status and limitations

Focused tests cover manifest integrity, parser behavior, state mappings, metrics, malformed numeric input, and Hyper-V workload conditions. Repository gates validate syntax, deterministic packaging, documentation synchronization, source security, and clean Checkmk registration. Live validation on representative Windows Server, Failover Cluster, S2D, and Hyper-V builds remains a deployment requirement because Microsoft cmdlet output varies by build, role, language, and feature availability.

See [Validation and release evidence](docs/VALIDATION.md).

## Migration, provenance, and license

The stable `s2d_hci_*` section, check, service, ruleset, and metric names are preserved from `Daniel-Dietz/S2D-Monitoring`. Do not run direct and spool-based virtualization collection simultaneously because duplicate sections are ambiguous.

The migration baseline is source commit `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`. See [Upstream provenance](docs/UPSTREAM_PROVENANCE.md).

This package retains the [PolyForm Internal Use License 1.0.0](LICENSE), which applies specifically to this package.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `s2d_hci_monitoring` version `1.0.0`; minimum Checkmk version `2.5.0`; maximum asserted version: 2.5.99.
- Canonical manifest: `s2d_hci_monitoring/src/info`; it declares 18 packaged files.
- No committed MKP artifact is present; build and validate the package from `src/` before installation.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/s2d_hci/agent_based/s2d_hci_fast.py`, `src/s2d_hci/agent_based/s2d_hci_health.py`, `src/s2d_hci/agent_based/s2d_hci_jobs.py`, `src/s2d_hci/agent_based/s2d_hci_perf.py`, `src/s2d_hci/agent_based/s2d_hci_storage.py`, `src/s2d_hci/agent_based/s2d_hci_virtualization.py`.
- **Rulesets:** `src/s2d_hci/rulesets/ruleset_s2d_hci.py`, `src/s2d_hci/rulesets/ruleset_s2d_hci_workloads.py`.
- **Graphing:** `src/s2d_hci/graphing/graphing_s2d_hci.py`.
- **Check manuals:** `src/s2d_hci/checkman/s2d_hci`.
- **Other packaged source:** `src/agents/config/s2d_hci_virtualization.json`, `src/agents/plugins/s2d_hci_fast.ps1`, `src/agents/plugins/s2d_hci_health.ps1`, `src/agents/plugins/s2d_hci_jobs.ps1`, `src/agents/plugins/s2d_hci_perf.ps1`, `src/agents/plugins/s2d_hci_storage.ps1`, `src/agents/plugins/s2d_hci_virtualization.ps1`, `src/agents/scripts/s2d_hci_virtualization_spool.ps1`.
- Registered check plug-in names: `s2d_hci_cluster_groups`, `s2d_hci_cluster_resources`, `s2d_hci_cluster_summary`, `s2d_hci_csv`, `s2d_hci_network_interfaces`, `s2d_hci_networks`, `s2d_hci_nodes`, `s2d_hci_performance_history`, `s2d_hci_physical_disks`, `s2d_hci_quorum`, `s2d_hci_s2d_state`, `s2d_hci_storage_health_report`, `s2d_hci_storage_jobs`, `s2d_hci_storage_pools`, `s2d_hci_storage_subsystems`, `s2d_hci_virtual_disks`, `s2d_hci_virtualization_checkpoints`, `s2d_hci_virtualization_hard_disks`, `s2d_hci_virtualization_host`, `s2d_hci_virtualization_network_adapters`, `s2d_hci_virtualization_replication`, `s2d_hci_virtualization_services`, `s2d_hci_virtualization_workloads`, `s2d_hci_volumes`.

### Validation

- Package-specific tests: `tests/test_manifest_integrity.py`, `tests/test_powershell_contracts.py`, `tests/test_s2d_hci_checks.py`, `tests/test_s2d_hci_virtualization.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `s2d_hci_csv`, `s2d_hci_networks`, `s2d_hci_nodes`, `s2d_hci_physical_disks`, `s2d_hci_quorum`, `s2d_hci_storage_jobs`, `s2d_hci_storage_pools`, `s2d_hci_virtual_disks`, `s2d_hci_virtualization_checkpoints`, `s2d_hci_virtualization_hard_disks`, `s2d_hci_virtualization_host`, `s2d_hci_virtualization_network_adapters`, `s2d_hci_virtualization_replication`, `s2d_hci_virtualization_services`, `s2d_hci_virtualization_workloads`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
