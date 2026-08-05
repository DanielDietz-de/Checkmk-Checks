# Unisphere PowerMax

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0p2-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

Special agent for Dell EMC Unisphere for PowerMax. Queries the Unisphere REST API at `https://<host>:<port>/univmax/restapi` and emits multiple Checkmk sections covering Storage Resource Pools, directors, port groups, masking views, volumes/ports, array performance, alert summaries, health scores and health checks.

## How it works

The special agent `agent_unisphere_powermax` authenticates with HTTP basic auth against the Unisphere REST API (default API version 100) and iterates over all Symmetrix systems returned by `/sloprovisioning/symmetrix`. By default it only queries systems flagged as `local`; remote Symmetrix systems can be enabled via a rule option. Results are printed as pipe-separated key/JSON lines under several section headers, with a 4-thread worker pool for masking-view detail queries and an on-disk cache under `$OMD_ROOT/tmp` for expensive masking view calls.

| Section | Data source / API |
| --- | --- |
| `unisphere_powermax_srp` | `/<v>/sloprovisioning/symmetrix/<id>/srp/<srp>` |
| `unisphere_powermax_director` | `/<v>/system/symmetrix/<id>/director/<dir>` |
| `unisphere_powermax_health_score` | `/<v>/system/symmetrix/<id>/health` |
| `unisphere_powermax_health_check` | `/<v>/system/symmetrix/<id>/health/health_check/<id>` |
| `unisphere_powermax_array_performance` | POST `/performance/Array/metrics` (Maximum + Average, 5 min window) |
| `unisphere_powermax_port_group` | `/<v>/sloprovisioning/symmetrix/<id>/portgroup` + port status |
| `unisphere_powermax_alerts` | `/<v>/system/alert_summary` |
| `unisphere_powermax_volume`, `unisphere_powermax_port` | masking view walk (cached) |

Each data source can be disabled individually through the WATO rule.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/unisphere_powermax/libexec/agent_unisphere_powermax` | Special agent (Python, uses `requests`). |
| `src/unisphere_powermax/server_side_calls/unisphere_powermax.py` | Builds the agent command line from rule parameters. |
| `src/unisphere_powermax/rulesets/rulesets.py` | Special-agent rule plus check-parameter rules for SRP / WP cache / health score / masking view / port group. |
| `src/unisphere_powermax/agent_based/unisphere_powermax_srp.py` | SRP effective/physical usage, data reduction ratio. |
| `src/unisphere_powermax/agent_based/unisphere_powermax_director.py` | Director status checks. |
| `src/unisphere_powermax/agent_based/unisphere_powermax_health_score.py` | Per-metric health score (lower levels). |
| `src/unisphere_powermax/agent_based/unisphere_powermax_health_check.py` | Symmetrix health check results. |
| `src/unisphere_powermax/agent_based/unisphere_powermax_array_performance.py` | Array performance + WP cache levels (Average / Maximum). |
| `src/unisphere_powermax/agent_based/unisphere_powermax_port_group.py` | Port-group / port state. |
| `src/unisphere_powermax/agent_based/unisphere_powermax_masking_view.py` | Masking view volume and port summaries. |
| `src/unisphere_powermax/agent_based/unisphere_powermax_alert.py` | Alert summaries (server + Symmetrix). |
| `src/unisphere_powermax/agent_based/utils.py` | Shared section parser. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a monitoring user on the Unisphere appliance with read access to the REST API.
3. Add the Unisphere host in Checkmk and configure the special agent rule (see below).

## Configuration

WATO rule: *Setup > Agents > Other integrations > Unisphere Powermax* (topic *Storage*).

| Parameter | Type | Meaning |
| --- | --- | --- |
| `username` | String (required) | Unisphere REST API user. |
| `password` | Password (required) | API password. |
| `port` | Integer (default 8443) | HTTPS port of Unisphere. |
| `api_version` | Integer (default 100) | REST API version prefix. |
| `use_ip` | Bool | Use the host's primary IP instead of its name for the HTTPS request. |
| `cache_time` | Integer (minutes, default 30) | Cache lifetime for masking view data. |
| `no_cert_check` | Bool | Disable SSL certificate verification. |
| `enable_remote_sym_checks` | Bool | Also query remote (non-local) Symmetrix systems. |
| `disable_get_srp_info` / `..._director_info` / `..._health_score_info` / `..._health_check_info` / `..._array_performance_info` / `..._port_group_info` / `..._alert_info` / `..._masking_view_info` | Bool | Disable individual data sources. |

A `_migrate` function silently upgrades older rule keys (`cache-time`, `useIP`, camelCase `disablegetXInfo`) to the new snake_case names.

Check parameter rules (topic *Storage*):

- *PowerMax SRP Effective usage* — upper % levels, default 80 / 90.
- *PowerMax SRP physical usage* — upper % levels, default 80 / 90.
- *PowerMax SRP Data Reduction Ratio* — lower levels on ratio, default 3.0 / 2.0.
- *PowerMax WP Cache usage* — upper % levels on Average and Maximum, default 80 / 90.
- *PowerMax Health Score* — lower % levels, default 90 / 80.
- *PowerMax Masking View Port Summary* — upper % levels.
- *PowerMax Masking View Volume Summary* — upper % levels.
- *PowerMax Port Group state* — upper % levels.

## Known limitations

- The agent uses a `--randomFailures` debug flag that can randomly flip port/volume status in the agent output — do not enable in production.
- The masking view section is refreshed only every `cache_time` minutes; shorter check intervals will see stale data.
- HTTP basic auth only; no OAuth / token support.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `unisphere_powermax` version `3.0.12`; minimum Checkmk version `2.3.0p2`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `unisphere_powermax/src/info`; it declares 14 packaged files.
- Repository MKP artifacts present: `unisphere_powermax-2.2.3.mkp`, `unisphere_powermax-2.2.4.mkp`, `unisphere_powermax-2.2.5.mkp`, `unisphere_powermax-3.0.0.mkp`, `unisphere_powermax-3.0.1.mkp`, `unisphere_powermax-3.0.10.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/unisphere_powermax/agent_based/unisphere_powermax_alert.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_array_performance.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_director.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_health_check.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_health_score.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_masking_view.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_port_group.py`, `src/unisphere_powermax/agent_based/unisphere_powermax_srp.py` and 1 more.
- **Server-side calls:** `src/unisphere_powermax/server_side_calls/unisphere_powermax.py`.
- **Rulesets:** `src/unisphere_powermax/rulesets/rulesets.py`.
- **Executables:** `src/unisphere_powermax/libexec/agent_unisphere_powermax`.
- **Check manuals:** `src/unisphere_powermax/checkman/unisphere_powermax_port_masking_view_port_summary`, `src/unisphere_powermax/checkman/unisphere_powermax_volume_masking_view_volume_summary`.
- Registered special-agent names: `unisphere_powermax`.
- Registered check plug-in names: `unisphere_powermax_alerts`, `unisphere_powermax_array_performance_perf_info`, `unisphere_powermax_array_performance_wp_cache`, `unisphere_powermax_director_status`, `unisphere_powermax_health_check`, `unisphere_powermax_health_score`, `unisphere_powermax_port_group_state`, `unisphere_powermax_port_masking_view_port_summary`, `unisphere_powermax_srp_data_reduction_ratio`, `unisphere_powermax_srp_effective_used`, `unisphere_powermax_srp_physical_used`, `unisphere_powermax_volume_masking_view_volume_summary`.

### Validation

- Package-specific tests: `tests/test_unisphere_powermax_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `check_mk`, `unisphere_powermax_alert`, `unisphere_powermax_alerts`, `unisphere_powermax_array_performance`, `unisphere_powermax_director`, `unisphere_powermax_health_check`, `unisphere_powermax_health_score`, `unisphere_powermax_port`, `unisphere_powermax_port_group`, `unisphere_powermax_srp`, `unisphere_powermax_volume`.
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
