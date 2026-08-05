# DELL EMC PowerMax

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0-blue)
<!-- compatibility-badges:end -->

Special agent for Dell EMC PowerMax (VMAX) arrays. It talks to the Unisphere for PowerMax REST API and produces services for Unisphere version, JVM/CPU/memory stats of the Unisphere server, server- and array-level alerts, and storage resource pool usage. TLS certificate verification is enabled by default, with support for a private CA bundle and an explicit temporary compatibility opt-out. This is a modernised port of the `dellpmax-agent` plugin originally published on the Checkmk Exchange by Mario Schwab and Achim Geisler.

## How it works

The special agent `agent_dellpmax` authenticates via HTTP basic auth against `https://<address>:<port>/univmax/restapi/` (default port 8443) and emits sections with `sep(124)`. The Checkmk password-store reference is resolved by the executable, requests use a bounded timeout, and contradictory private-CA plus verification-opt-out settings are rejected before command construction.

- `version` -> `<<<dellpmax_systeminfo>>>` — Unisphere version string.
- `management/RuntimeUsage/read` -> `<<<dellpmax_systemstats>>>` — heap (max/used), cpu usage, memory total/used. Split into three services (`Heap`, `CPU`, `Memory`) reusing `cmk.plugins.lib.memory` and `cpu_util`.
- `92/vvol/symmetrix` + `92/vvol/symmetrix/<id>` — discovers the local array id.
- `92/system/alert_summary` -> `<<<dellpmax_server_alerts>>>` and `<<<dellpmax_symm_alerts>>>` — unacknowledged warning/critical/fatal counts.
- `92/sloprovisioning/symmetrix/<id>/srp/...` -> `<<<dellpmax_storage_pools>>>` — per-SRP subscribed, snapshot, usable and effective used capacities.

Each SRP produces three services (`Subscribed Capacity <srp>`, `Snapshot Capacity <srp>`, `Usable Capacity <srp>`) with hardcoded 80/90 WARN/CRIT thresholds on the percentage values.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/dell_pmax/libexec/agent_dellpmax` | Special agent and bounded Unisphere REST client. |
| `src/dell_pmax/agent_based/dellpmax_info.py` | `Version Info` service. |
| `src/dell_pmax/agent_based/dellpmax_system_stats.py` | `Heap`, `CPU`, `Memory` services from Unisphere runtime usage. |
| `src/dell_pmax/agent_based/dellpmax_alerts_server.py` | `Server alerts` service. |
| `src/dell_pmax/agent_based/dellpmax_alerts_symm.py` | `Array alerts` and `Performance alerts` services. |
| `src/dell_pmax/agent_based/dellpmax_storage_pools.py` | `Subscribed Capacity`, `Snapshot Capacity`, `Usable Capacity` per SRP. |
| `src/dell_pmax/rulesets/agent_dellpmax.py` | Special-agent rule for credentials, port, timeout, and TLS controls. |
| `src/dell_pmax/server_side_calls/agent_pmax.py` | Validated command construction using the Checkmk password store. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a host for the Unisphere appliance and configure the special-agent rule below.
3. Use an API account with only the read-only monitoring role.
4. For a private PKI, make the CA bundle readable by the Checkmk site user and configure its absolute path.
5. Run service discovery.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> Dell Powermax**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `username` | String | Unisphere user with the read-only monitoring role. |
| `password` | Password | Password retained as a Checkmk password-store reference until agent-side resolution. |
| `port` | Integer | Unisphere REST API port; default `8443`. |
| `timeout` | Float | Bounded request timeout in seconds; default `30`. |
| `ca_file` | String | Optional private CA bundle path used for TLS verification. |
| `no_cert_check` | BooleanChoice | Explicit temporary certificate-verification opt-out. It is mutually exclusive with `ca_file`. |

Prefer the system trust store or `ca_file`. Use `no_cert_check` only as a documented temporary exception while repairing the appliance certificate chain.

## Services & metrics

- **Services:** `Version Info`, `Heap`, `CPU`, `Memory`, `Server alerts`, `Array alerts`, `Performance alerts`, `Subscribed Capacity <srp>`, `Snapshot Capacity <srp>`, `Usable Capacity <srp>`.
- **State logic:**
  - Alerts: OK at 0, WARN/CRIT when warning/critical/fatal counters are non-zero.
  - Subscribed/Usable capacity: WARN at 80%, CRIT at 90%.
  - Snapshot capacity: always OK.

## Known limitations

- The WARN/CRIT thresholds for storage pools are hardcoded in the check plugin and are not exposed through the ruleset.
- Requests are not retried; transient API or network failures are reported by the special agent and retried on the next Checkmk execution.
- The integration depends on the Unisphere REST API paths currently used by supported PowerMax releases; validate after appliance upgrades.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `dell_pmax` version `2.0.4`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `dell_pmax/src/info`; it declares 8 packaged files.
- Repository MKP artifacts present: `dell_pmax-1.0.1.mkp`, `dell_pmax-2.0.0.mkp`, `dell_pmax-2.0.1.mkp`, `dell_pmax-2.0.2.mkp`, `dell_pmax-2.0.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/dell_pmax/agent_based/dellpmax_alerts_server.py`, `src/dell_pmax/agent_based/dellpmax_alerts_symm.py`, `src/dell_pmax/agent_based/dellpmax_info.py`, `src/dell_pmax/agent_based/dellpmax_storage_pools.py`, `src/dell_pmax/agent_based/dellpmax_system_stats.py`.
- **Server-side calls:** `src/dell_pmax/server_side_calls/agent_pmax.py`.
- **Rulesets:** `src/dell_pmax/rulesets/agent_dellpmax.py`.
- **Executables:** `src/dell_pmax/libexec/agent_dellpmax`.
- Registered special-agent names: `dellpmax`.
- Registered check plug-in names: `dellpmax_server_alerts`, `dellpmax_storage_pools`, `dellpmax_storage_pools_snapshot`, `dellpmax_storage_pools_subscribed`, `dellpmax_symm_alerts_arrays`, `dellpmax_symm_alerts_performance`, `dellpmax_systeminfo`, `dellpmax_systemstats_cpu`, `dellpmax_systemstats_heap`, `dellpmax_systemstats_mem`.

### Validation

- Package-specific tests: `tests/test_dell_pmax_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `dellpmax_server_alerts`, `dellpmax_storage_pools`, `dellpmax_symm_alerts`, `dellpmax_systeminfo`, `dellpmax_systemstats`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
## TLS trust and private CAs

TLS certificate verification remains enabled by default. To preserve Checkmk site isolation, the integration disables Requests proxy and `.netrc` inheritance with `trust_env = False` and passes certificate trust explicitly. The trust order is:

1. the rule's **Custom CA bundle** (`ca_file`);
2. `REQUESTS_CA_BUNDLE` from the Checkmk site environment;
3. `CURL_CA_BUNDLE` from the Checkmk site environment;
4. the operating system trust store.

The configured bundle must exist as a regular PEM file on the Checkmk server. An explicit certificate-verification opt-out, where supported, is mutually exclusive with a custom CA bundle and should be used only as a temporary compatibility measure. Environment CA variables are read deliberately even though proxy and `.netrc` inheritance remain disabled.

Troubleshooting order: verify the endpoint name matches the certificate, confirm the PEM path is readable by the site user, test the CA chain with the same site environment, and use the verification opt-out only to isolate a trust-chain problem. Removing `ca_file` falls back automatically to the site variables and then to the system trust store.
