# s2d_hci_monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.5.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0p9-blue) ![usable until](https://img.shields.io/badge/usable%20until-2.5.99-green)
<!-- compatibility-badges:end -->

`s2d_hci_monitoring` monitors Microsoft Windows Failover Clustering, Storage Spaces Direct, HCI storage, and Hyper-V workloads with split, read-only Windows collectors and Checkmk Check API V2 plug-ins.

The package is designed for Checkmk 2.5.0 through 2.5.99. It does not support Checkmk 2.4 or legacy Check API V1 paths.

## Scope

The package provides services for:

- cluster identity, quorum, nodes, networks, network interfaces, groups, and resources;
- Cluster Shared Volumes, storage pools, virtual disks, volumes, physical disks, storage jobs, S2D state, storage subsystems, and storage-health reports;
- Hyper-V host availability, virtual machine state, CPU and memory pressure, integration services, replication, checkpoints, virtual network adapters, and virtual hard disks;
- optional cluster performance-history availability.

It does not change cluster, storage, Hyper-V, networking, service, registry, or firewall configuration. It does not replace Microsoft cluster validation, backup verification, capacity planning, or application-level monitoring inside virtual machines.

## Compatibility and prerequisites

| Component | Requirement |
| --- | --- |
| Checkmk | 2.5.0 through 2.5.99 |
| Windows | Windows Server with the monitored Failover Clustering, Storage Spaces Direct, and/or Hyper-V roles |
| PowerShell | Windows PowerShell 5.1 or newer |
| Modules | `FailoverClusters`, `Storage`, and `Hyper-V` as required by the selected collectors |
| Agent identity | Sufficient local read access to the relevant Microsoft management cmdlets |
| Workload spool mode | A dedicated gMSA with read-only Hyper-V visibility and write access only to the Checkmk spool directory |

The upper compatibility limit is an evidence boundary, not a statement that later Checkmk releases are incompatible. Revalidate and update the manifest before extending it.

## Architecture

The MKP installs server-side Checkmk plug-ins and makes Windows agent files available for deployment. Collection is deliberately split by cost and expected cache interval:

| Collector | Data | Recommended interval |
| --- | --- | ---: |
| `s2d_hci_fast.ps1` | quorum, nodes, networks, groups, resources | 60–120 seconds |
| `s2d_hci_storage.ps1` | CSVs, pools, virtual disks, volumes, physical disks | 300 seconds |
| `s2d_hci_jobs.ps1` | storage jobs and repair/resynchronization progress | 300 seconds |
| `s2d_hci_health.ps1` | S2D state, subsystems, storage-health reports | 600 seconds |
| `s2d_hci_perf.ps1` | optional cluster performance history | 900 seconds |
| `s2d_hci_virtualization.ps1` | Hyper-V host and workload inventory/state | 120–300 seconds |

The collectors emit one JSON object per line below named Checkmk agent sections. Server-side parsers discard malformed individual lines while retaining valid data from the same section. Expensive collectors must be cached or executed asynchronously; do not add sleeps inside the scripts.

For workload collection under a dedicated identity, the scheduled task executes `s2d_hci_virtualization_spool.ps1`. The wrapper validates that collector and spool paths remain below the Checkmk agent root, writes to a temporary file, and atomically replaces the spool file. The numeric `600_` prefix gives Checkmk a stale-data lifetime.

See [Architecture](docs/ARCHITECTURE.md) and [gMSA spool collector](docs/GMSA_SPOOL_COLLECTOR.md).

## Installation

### 1. Obtain a validated package

On `master`, download the current MKP and matching checksum from this directory. On an unmerged pull request, use only the MKP artifact produced by that pull request’s successful repository validation workflow.

```bash
sha256sum --check s2d_hci_monitoring-1.0.0.mkp.sha256
```

Do not substitute an older same-name package and do not install an unverified local build in production.

### 2. Install on the Checkmk site

As the site user, use the `mkp` syntax supported by the installed Checkmk 2.5 release, or use **Setup > Maintenance > Extension packages**:

```bash
mkp add /path/to/s2d_hci_monitoring-1.0.0.mkp
mkp enable s2d_hci_monitoring 1.0.0
cmk -R
```

### 3. Deploy Windows collectors

The enabled MKP exposes the agent files below the site’s agent download area. Deploy only the collectors applicable to each node. Place cached collectors in the Windows agent’s version-appropriate plug-in interval directory rather than running every collector synchronously.

Typical Checkmk agent root:

```text
C:\ProgramData\checkmk\agent\
```

For example:

```text
plugins\120\s2d_hci_fast.ps1
plugins\300\s2d_hci_storage.ps1
plugins\300\s2d_hci_jobs.ps1
plugins\600\s2d_hci_health.ps1
plugins\900\s2d_hci_perf.ps1
```

Use the gMSA spool procedure for virtualization collection when the Checkmk agent service identity cannot or should not receive Hyper-V read permissions.

### 4. Rediscover and validate

```bash
cmk-validate-plugins
cmk -d hci-node | grep '^<<<s2d_hci_'
cmk -IIv hci-node
cmk -nv hci-node
```

Accept only the expected services and verify representative OK, WARN, CRIT, and UNKNOWN conditions before broader rollout.

The complete procedure is in [Installation and operations](docs/INSTALLATION_AND_OPERATIONS.md).

## Configuration

Checkmk provides rules for:

- CSV free-space warning and critical levels; defaults: 15% and 10%;
- volume free-space warning and critical levels; defaults: 15% and 10%;
- workload CPU warning and critical levels; defaults: 80% and 95%;
- workload memory-pressure warning and critical levels; defaults: 100% and 120%;
- retained checkpoint age warning and critical levels; defaults: 24 and 72 hours.

Apply rules narrowly to the intended cluster nodes and items. The collectors themselves have no embedded credentials and no network destinations.

The virtualization spool configuration contains only local paths:

```json
{
  "collector_path": "C:\\ProgramData\\checkmk\\agent\\plugins\\s2d_hci_virtualization.ps1",
  "spool_file": "C:\\ProgramData\\checkmk\\agent\\spool\\600_s2d_hci_virtualization.txt",
  "require_paths_under_agent_root": true
}
```

Keep `require_paths_under_agent_root` enabled. Do not place passwords, tokens, account secrets, or production inventory in this file.

## State and failure behavior

- Known healthy/online/running states are OK.
- Draining, degraded, warning, suspended, saved, resynchronizing, and active storage-job states are WARN where operator attention is appropriate.
- Down, offline, failed, detached, missing Hyper-V module, disconnected virtual NIC, and unhealthy states are CRIT.
- Unknown vendor values, missing expected items, malformed or absent section data, and unsupported optional cmdlets are UNKNOWN.
- A completed storage job disappears from collector output; a formerly discovered missing job is reported OK so transient job services can age out without a false failure.
- Invalid JSON lines are ignored. A fully invalid or empty section produces no usable data and therefore no false healthy state.
- The spool filename’s numeric prefix causes stale output to expire. A failed scheduled task must not leave indefinitely valid workload data.

## Security

All packaged collectors are intended to be read-only. Review every change for accidental use of mutating Microsoft cmdlets. Do not grant domain-administrator, cluster-administrator, local-administrator, or Hyper-V management rights when narrower read access is sufficient.

The gMSA task installer:

- accepts only a gMSA name ending in `$`;
- uses the Scheduled Tasks `ServiceAccount` logon type;
- never accepts or stores a password;
- restricts collector, configuration, and spool paths to the Checkmk agent root;
- invokes PowerShell without an execution-policy bypass;
- supports `-WhatIf` and `-DryRun` before applying changes.

Protect the agent root and spool directory with NTFS ACLs. The gMSA requires read/execute access to the collector and wrapper, read access to the non-secret JSON file, and create/replace access only in the spool directory. Do not log complete VM paths or IP inventories outside the normal Checkmk data path without reviewing their sensitivity.

See [Security](docs/SECURITY.md). Vulnerabilities must follow the repository-level `SECURITY.md` process.

## Troubleshooting

1. Run each collector interactively under the same identity used by Checkmk or the scheduled task.
2. Confirm required PowerShell modules and cmdlets are installed.
3. Inspect raw agent output for the expected `<<<s2d_hci_*>>>` sections and JSON lines.
4. Run `cmk-validate-plugins`, discovery, and an individual check execution on the Checkmk site.
5. Validate gMSA permissions with `tools/windows/Test-S2DHciVirtualizationCollectorIdentity.ps1`.
6. Inspect the scheduled task’s last result and the timestamp of `600_s2d_hci_virtualization.txt`.

Sanitize hostnames, domain names, VM names, paths, serial numbers, IP addresses, and cluster topology before attaching diagnostics to a public issue.

Detailed diagnostics are in [Installation and operations](docs/INSTALLATION_AND_OPERATIONS.md).

## Upgrade and migration

The package keeps the original `s2d_hci_*` section names, check names, service names, metrics, and ruleset names from the source repository. Migration from `Daniel-Dietz/S2D-Monitoring` therefore does not intentionally rename discovered services or saved rules.

Before upgrading:

1. save the current MKP and Windows agent files;
2. record custom rules and scheduled-task settings;
3. install the new MKP on a test site;
4. compare raw sections and rediscovery output;
5. update host-side files and the scheduled task as one controlled change;
6. retain the previous package and files for rollback.

Do not run both direct virtualization collection and the spool collector simultaneously because duplicate sections can produce ambiguous data.

## Removal and rollback

1. Disable and remove the MKP through Checkmk Setup or the supported `mkp` commands.
2. Reload the site with `cmk -R`.
3. Remove the six collector scripts from Windows agent plug-in directories.
4. Remove the scheduled task, wrapper, JSON configuration, and spool file when gMSA mode was used.
5. Remove the dedicated gMSA permissions or the account itself only after confirming no other service uses it.
6. Rediscover affected hosts and remove vanished services under normal change control.

Removing the MKP does not automatically remove files or scheduled tasks from Windows nodes.

## Validation evidence and limitations

Automated tests cover manifest completeness, parser behavior, major state mappings, metrics, malformed percentage input, and Hyper-V workload conditions. Repository CI additionally validates syntax, documentation, security policy, deterministic packaging, and registration in clean Checkmk 2.5 environments.

Live-system validation is still required against representative Windows Server, Failover Cluster, Storage Spaces Direct, and Hyper-V versions. Microsoft cmdlet output can vary by operating-system build, installed role, language, and feature availability. Optional performance history and storage-health reports are explicitly UNKNOWN when their cmdlets are unavailable.

The package currently has no Agent Bakery implementation. The MKP ships agent files, but administrators must deploy or distribute them through their normal controlled Windows agent process.

## License and provenance

This package is licensed separately under the [PolyForm Internal Use License 1.0.0](LICENSE), preserved from the source repository. That package-specific license takes precedence for these files over the target repository’s general license text.

The HCI implementation was migrated from `Daniel-Dietz/S2D-Monitoring` at source commit `c6aa39d8fa62c1a550c07308f99e75c94ba5a7c2`. See [Upstream provenance](docs/UPSTREAM_PROVENANCE.md).

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

- **Agent-based checks:** `src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_fast.py`, `src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_health.py`, `src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_jobs.py`, `src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_perf.py`, `src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_storage.py`, `src/cmk_addons_plugins/s2d_hci/agent_based/s2d_hci_virtualization.py`.
- **Rulesets:** `src/cmk_addons_plugins/s2d_hci/rulesets/ruleset_s2d_hci.py`, `src/cmk_addons_plugins/s2d_hci/rulesets/ruleset_s2d_hci_workloads.py`.
- **Graphing:** `src/cmk_addons_plugins/s2d_hci/graphing/graphing_s2d_hci.py`.
- **Check manuals:** `src/cmk_addons_plugins/s2d_hci/checkman/s2d_hci`.
- **Other packaged source:** `src/agents/config/s2d_hci_virtualization.json`, `src/agents/plugins/s2d_hci_fast.ps1`, `src/agents/plugins/s2d_hci_health.ps1`, `src/agents/plugins/s2d_hci_jobs.ps1`, `src/agents/plugins/s2d_hci_perf.ps1`, `src/agents/plugins/s2d_hci_storage.ps1`, `src/agents/plugins/s2d_hci_virtualization.ps1`, `src/agents/scripts/s2d_hci_virtualization_spool.ps1`.
- Registered check plug-in names: `s2d_hci_cluster_groups`, `s2d_hci_cluster_resources`, `s2d_hci_cluster_summary`, `s2d_hci_csv`, `s2d_hci_network_interfaces`, `s2d_hci_networks`, `s2d_hci_nodes`, `s2d_hci_performance_history`, `s2d_hci_physical_disks`, `s2d_hci_quorum`, `s2d_hci_s2d_state`, `s2d_hci_storage_health_report`, `s2d_hci_storage_jobs`, `s2d_hci_storage_pools`, `s2d_hci_storage_subsystems`, `s2d_hci_virtual_disks`, `s2d_hci_virtualization_checkpoints`, `s2d_hci_virtualization_hard_disks`, `s2d_hci_virtualization_host`, `s2d_hci_virtualization_network_adapters`, `s2d_hci_virtualization_replication`, `s2d_hci_virtualization_services`, `s2d_hci_virtualization_workloads`, `s2d_hci_volumes`.

### Validation

- Package-specific tests: `tests/test_manifest_integrity.py`, `tests/test_s2d_hci_checks.py`, `tests/test_s2d_hci_virtualization.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `s2d_hci_csv`, `s2d_hci_networks`, `s2d_hci_nodes`, `s2d_hci_physical_disks`, `s2d_hci_quorum`, `s2d_hci_storage_jobs`, `s2d_hci_storage_pools`, `s2d_hci_virtual_disks`, `s2d_hci_virtualization_checkpoints`, `s2d_hci_virtualization_hard_disks`, `s2d_hci_virtualization_host`, `s2d_hci_virtualization_network_adapters`, `s2d_hci_virtualization_replication`, `s2d_hci_virtualization_services`, `s2d_hci_virtualization_workloads`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
