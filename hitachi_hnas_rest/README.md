# Hitachi HNAS via REST API

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p18-blue)
<!-- compatibility-badges:end -->

Special agent based monitoring of Hitachi NAS (HNAS) systems using the
NAS File Storage REST API (v8, TCP port 8444).

Replaces a legacy Nagios plugin (`nagiosplugin` based) with a native
Checkmk plugin.

## Monitored components

| Service | Source | Description |
|---|---|---|
| HNAS Filesystem | `/v8/storage/filesystems` | Space usage (levels, default 80%/90%), thin provisioning state, mount status |
| HNAS Snapshots | `/v8/storage/filesystems/{id}/snapshots` | Snapshot count, age of oldest snapshot, time since last snapshot |
| HNAS Storage Pool | `/v8/storage/storage-pools` | Space usage (levels, default 80%/90%), health state |
| HNAS EVS | `/v8/storage/virtual-servers` | Virtual server status (ONLINE/DISABLED/OFFLINE/NOT_CONFIGURED) |
| HNAS Node | `/v8/storage/nodes` | Cluster node status, model, firmware, uptime |
| HNAS System Drive | `/v8/storage/system-drives` | System drive status, degraded state |

## Setup

1. Install the MKP.
2. Create an API key on the HNAS (`apikey-create`, recommended) or use
   an API user with password.
3. Configure the rule *Hitachi HNAS via REST API* under
   *Setup > Agents > Other integrations*.

Authentication is done either via the `X-Api-Key` header (recommended
by Hitachi) or via `X-Subsystem-User`/`X-Subsystem-Password` headers
for backward compatibility.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `hitachi_hnas_rest` version `1.0.2`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `hitachi_hnas_rest/src/info`; it declares 19 packaged files.
- Repository MKP artifacts present: `hitachi_hnas_rest-1.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/hitachi_hnas_rest/agent_based/filesystems.py`, `src/hitachi_hnas_rest/agent_based/nodes.py`, `src/hitachi_hnas_rest/agent_based/snapshots.py`, `src/hitachi_hnas_rest/agent_based/storage_pools.py`, `src/hitachi_hnas_rest/agent_based/system_drives.py`, `src/hitachi_hnas_rest/agent_based/virtual_servers.py`.
- **Server-side calls:** `src/hitachi_hnas_rest/server_side_calls/agent.py`.
- **Rulesets:** `src/hitachi_hnas_rest/rulesets/agent.py`, `src/hitachi_hnas_rest/rulesets/filesystems.py`, `src/hitachi_hnas_rest/rulesets/snapshots.py`, `src/hitachi_hnas_rest/rulesets/storage_pools.py`.
- **Executables:** `src/hitachi_hnas_rest/libexec/agent_hitachi_hnas_rest`.
- **Graphing:** `src/hitachi_hnas_rest/graphing/metrics.py`.
- **Check manuals:** `src/hitachi_hnas_rest/checkman/hitachi_hnas_rest_filesystems`, `src/hitachi_hnas_rest/checkman/hitachi_hnas_rest_nodes`, `src/hitachi_hnas_rest/checkman/hitachi_hnas_rest_snapshots`, `src/hitachi_hnas_rest/checkman/hitachi_hnas_rest_storage_pools`, `src/hitachi_hnas_rest/checkman/hitachi_hnas_rest_system_drives`, `src/hitachi_hnas_rest/checkman/hitachi_hnas_rest_virtual_servers`.
- Registered special-agent names: `hitachi_hnas_rest`.
- Registered check plug-in names: `hitachi_hnas_rest_filesystems`, `hitachi_hnas_rest_nodes`, `hitachi_hnas_rest_snapshots`, `hitachi_hnas_rest_storage_pools`, `hitachi_hnas_rest_system_drives`, `hitachi_hnas_rest_virtual_servers`.

### Validation

- Package-specific tests: `tests/test_hitachi_hnas_rest_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `hitachi_hnas_rest_filesystems`, `hitachi_hnas_rest_nodes`, `hitachi_hnas_rest_snapshots`, `hitachi_hnas_rest_storage_pools`, `hitachi_hnas_rest_system_drives`, `hitachi_hnas_rest_virtual_servers`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
