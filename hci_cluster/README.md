# HCI Cluster Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p25-blue)
<!-- compatibility-badges:end -->

Monitoring for Microsoft Storage Spaces Direct / Failover Cluster (HCI) environments. A PowerShell agent plugin on a Windows host queries cluster state via the FailoverClusters cmdlets and produces sections that are evaluated by several check plugins: nodes, cluster resources, S2D storage pools, virtual disks, storage jobs, and volume performance.

## How it works

1. The Bakery deploys `hci_cluster.ps1` to Windows hosts together with a generated `hci_cluster.cfg.ps1` that sets `$domain`, `$FilterTyp` (`None` / `Inclusion` / `Exclusion`), and `$FilterPattern`.
2. The plugin connects to the cluster (the Checkmk agent user needs permissions to query cluster information) and prints several sections.
3. Each section is parsed into a dict keyed by an identifier and evaluated by its own check plugin.

Sections and services produced:

| Section | Service name | State logic |
| --- | --- | --- |
| `hci_cluster_nodes` | `Node <Name>` | OK when `State == Up`, else CRIT |
| `hci_cluster_resources` | `Resource <Name>` | OK when `State == Online`, else CRIT |
| `hci_s2d_storage_pools` | `Storage Pool <DeviceId>` | OK when `OperationalStatus == OK`, else CRIT |
| `hci_virtual_disks` | `Virtual Disk <FriendlyName>` | OK when `OperationalStatus == OK`, else CRIT |
| `hci_storage_jobs` | `Storage Jobs` | OK if no jobs, CRIT while any job is listed (a running job is treated as bad even in state `Completed`) |
| `hci_s2d_volume_performance` / `hci_cluster_performance` | `Storage Pool Performance` | Informational: IOPS, latency, throughput, size; cluster mode also reports CsvCache metrics |

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/hci_cluster.ps1` | PowerShell agent plugin that queries the cluster and emits all sections. |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_helper.py` | Shared parsers (`parse_list`, `parse_multi_list`). |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_cluster_nodes.py` | Cluster node check. |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_cluster_resources.py` | Cluster resource check. |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_s2d-storage-pools.py` | S2D storage pool check. |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_virtual_disks.py` | Virtual disk check. |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_storage_jobs.py` | Storage jobs check. |
| `src/cmk_addons_plugins/hci_cluster/agent_based/hci_s2d_volume_performance.py` | Volume / cluster performance metrics. |
| `src/lib/python3/cmk/base/cee/plugins/bakery/hci_cluster.py` | Bakery hook registering the plugin and config. |
| `src/cmk_addons_plugins/hci_cluster/rulesets/bakery.py` | WATO ruleset for the Bakery config. |

## Installation

1. Install the MKP on the Checkmk site.
2. Deploy the plugin via the Agent Bakery rule *HCI Cluster Monitoring (Windows)* to a Windows host that has permission to query the cluster (domain account with cluster access).
3. Bake and roll out the agent; run service discovery on the host.

## Configuration

Bakery rule: **Agent rules -> HCI Cluster Monitoring (Windows)**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `domain` | text | AD domain to run the cluster query against. |
| `filter_type` | `None` / `Inclusion` / `Exclusion` | How `filter_pattern` is applied when enumerating cluster objects. |
| `filter_pattern` | text | Pattern used together with `filter_type` (e.g. `HCI`). Optional. |

## Known limitations

- The Bakery ruleset still uses the legacy pre-2.3 WATO API (`cmk.gui.plugins.wato` / `rulespec_registry`) while the checks themselves are on `cmk.agent_based.v2`.
- `hci_storage_jobs` intentionally reports CRIT whenever any job is listed, including `Completed`, because the Windows API keeps completed jobs visible.
- `hci_s2d_volume_performance` uses `render.timespan` for IOPS-like metrics — a cosmetic quirk kept from the original implementation.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `hci_cluster` version `2.0.2`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `hci_cluster/src/info`; it declares 10 packaged files.
- Repository MKP artifacts present: `hci_cluster-1.0.1.mkp`, `hci_cluster-1.0.mkp`, `hci_cluster-1.1.0.mkp`, `hci_cluster-1.1.1.mkp`, `hci_cluster-1.2.0.mkp`, `hci_cluster-1.2.1.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/hci_cluster/agent_based/hci_cluster_nodes.py`, `src/hci_cluster/agent_based/hci_cluster_resources.py`, `src/hci_cluster/agent_based/hci_helper.py`, `src/hci_cluster/agent_based/hci_s2d-storage-pools.py`, `src/hci_cluster/agent_based/hci_s2d_volume_performance.py`, `src/hci_cluster/agent_based/hci_storage_jobs.py`, `src/hci_cluster/agent_based/hci_virtual_disks.py`.
- **Rulesets:** `src/hci_cluster/rulesets/bakery.py`.
- **Bakery:** `src/lib/python3/cmk/base/cee/plugins/bakery/hci_cluster.py`.
- **Other packaged source:** `src/agents/plugins/hci_cluster.ps1`.
- Registered check plug-in names: `hci_cluster_nodes`, `hci_cluster_performance`, `hci_cluster_resources`, `hci_s2d_storage_pools`, `hci_s2d_volume_performance`, `hci_storage_jobs`, `hci_virtual_disks`.

### Validation

- Package-specific tests: `tests/test_hci_cluster_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `hci_cluster_nodes`, `hci_cluster_performance`, `hci_cluster_resources`, `hci_s2d_storage_pools`, `hci_s2d_volume_performance`, `hci_storage_jobs`, `hci_storage_pools`, `hci_virtual_disks`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
