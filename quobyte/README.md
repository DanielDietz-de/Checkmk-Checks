# Quobyte Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Special agent for Quobyte storage clusters. Talks to the Quobyte JSON-RPC
WebAPI and emits piggyback output for each cluster host, covering
services, health manager, devices, volumes and quotas. Ships check
plugins, a WATO rule, graphing definitions and a server-side-calls
binding.

## How it works

The special agent [`agent_quobyte`](src/quobyte/libexec/agent_quobyte) is
invoked with API URL, username, password, timeout and an optional explicit
CA bundle. It POSTs JSON-RPC calls and emits the following sections:

- `<<<quobyte_services>>>` (piggybacked per service host): list of
  service types and their `is_available` flag from `getServices`.
- `<<<quobyte_healthmanager>>>`: full `health_manager_status` dict from
  `getHealthManagerStatus` (one `key value` line each).
- `<<<quobyte_devices>>>` (piggybacked per device host): device id,
  serial, label, used/total bytes, status, LED status, mount path and
  health for each entry from `getDeviceList`.
- `<<<quobyte_volumes>>>`: per-volume logical/disk/allocated bytes plus
  file and directory counts from `getVolumeList`.
- `<<<quobyte_quotas>>>`: per quota entry (`[[[<type> <consumer_type>
  <identifier>]]]`) with `limit`, `usage`, `limit_type` and `tenant_id`,
  resolving volume UUIDs to volume names.

Check plugins under `src/quobyte/agent_based/` consume these sections:

| File | Section |
| --- | --- |
| `devices.py` | `quobyte_devices` - one service per device, CRIT if not healthy. |
| `healthmanager.py` | `quobyte_healthmanager` - health manager status overview. |
| `quota.py` | `quobyte_quotas` - one service per quota, usage vs. limit. |
| `services.py` | `quobyte_services` - one service per Quobyte component on a host. |
| `volumes.py` | `quobyte_volumes` - one service per volume. |

Graph, metric and perfometer definitions live under `src/quobyte/graphing/`.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/quobyte/libexec/agent_quobyte` | Special agent (JSON-RPC client to the Quobyte WebAPI). |
| `src/quobyte/server_side_calls/quobyte.py` | Server-side-call wiring: preserves the password-store reference and passes URL, user, timeout and optional CA bundle as named arguments. |
| `src/quobyte/rulesets/agent.py` | WATO special-agent ruleset `quobyte`. |
| `src/quobyte/rulesets/volumes.py` | WATO ruleset for volume check parameters. |
| `src/quobyte/agent_based/devices.py` | Devices check. |
| `src/quobyte/agent_based/healthmanager.py` | Health manager check. |
| `src/quobyte/agent_based/quota.py` | Quotas check. |
| `src/quobyte/agent_based/services.py` | Services check. |
| `src/quobyte/agent_based/volumes.py` | Volumes check. |
| `src/quobyte/graphing/graphs.py` | Graph definitions. |
| `src/quobyte/graphing/metrics.py` | Metric definitions. |
| `src/quobyte/graphing/perfometer.py` | Perfometer definitions. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a Checkmk host for the Quobyte cluster.
3. Configure the special agent via *Setup -> Agents -> Other integrations
   -> Quobyte via WebAPI*. Provide the API URL, a user with read access
   and the matching password; optionally override the timeout and provide
   an absolute PEM CA-bundle path for a private certificate authority.
4. Run service discovery on the cluster host. Additional services will
   appear on piggyback hosts named after the Quobyte service/device
   hosts.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> Quobyte via WebAPI**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `api_url` | `String` (required) | Full URL of the Quobyte JSON-RPC endpoint. |
| `username` | `String` (required) | API user. |
| `password` | `Password` (required) | API password stored through Checkmk's password store. |
| `ca_file` | `String` (optional) | Absolute PEM CA-bundle path on the Checkmk server. Overrides `REQUESTS_CA_BUNDLE`, then `CURL_CA_BUNDLE`. |
| `timeout` | `TimeSpan` (optional, default 2.5 s) | Request timeout. |

A separate ruleset is available for volume check parameters under the
normal *Parameters for discovered services* tree.

## Services & metrics

- Devices services (piggyback, one per device) with usage and health.
- Health manager overview service.
- One service per Quobyte component per host.
- One service per volume (with space and file/dir counters).
- One service per quota (usage vs. limit).

## Known limitations

- Ambient proxy and netrc settings are intentionally ignored. Certificate
  trust is retained explicitly with this precedence: rule `ca_file`,
  `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, then the system trust store.
- Quota parsing assumes a single `current_usage` entry per quota - the
  source explicitly notes this may be wrong for multi-metric quotas.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `quobyte` version `2.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `quobyte/src/info`; it declares 14 packaged files.
- Repository MKP artifacts present: `quobyte-1.0.0.mkp`, `quobyte-1.1.0.mkp`, `quobyte-1.1.1.mkp`, `quobyte-1.1.2.mkp`, `quobyte-1.1.3.mkp`, `quobyte-1.1.4.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/quobyte/agent_based/devices.py`, `src/quobyte/agent_based/healthmanager.py`, `src/quobyte/agent_based/quota.py`, `src/quobyte/agent_based/services.py`, `src/quobyte/agent_based/volumes.py`.
- **Server-side calls:** `src/quobyte/server_side_calls/quobyte.py`.
- **Rulesets:** `src/quobyte/rulesets/agent.py`, `src/quobyte/rulesets/devices.py`, `src/quobyte/rulesets/volumes.py`.
- **Executables:** `src/quobyte/libexec/agent_quobyte`.
- **Graphing:** `src/quobyte/graphing/graphs.py`, `src/quobyte/graphing/metrics.py`, `src/quobyte/graphing/perfometer.py`.
- **Check manuals:** `src/quobyte/checkman/quobyte_devices`.
- Registered special-agent names: `quobyte`.
- Registered check plug-in names: `quobyte_devices`, `quobyte_healthmanager`, `quobyte_quotas`, `quobyte_services`, `quobyte_volumes`.

### Validation

- Package-specific tests: `tests/test_quobyte_secret_command_arguments.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `quobyte_devices`, `quobyte_healthmanager`, `quobyte_quotas`, `quobyte_services`, `quobyte_volumes`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
## HTTP endpoint compatibility

For HTTP endpoints, CA bundle settings and CA environment variables are not evaluated because no TLS trust chain exists.
