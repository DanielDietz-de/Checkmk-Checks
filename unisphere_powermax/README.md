# Unisphere PowerMax

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0p2-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

Special agent for Dell EMC Unisphere for PowerMax. It collects SRPs, directors, health scores and checks, array performance, port groups, alerts, masking-view volumes, and masking-view ports.

## Deterministic collection model

- Synthetic `--randomFailures` behavior was removed completely.
- Debug output never prints parsed command-line arguments, credentials, request payloads, response bodies, or response headers.
- Selected data sources run deterministically and sequentially. A transport, API, schema, cache, or data-source error fails the complete run.
- Agent output is accumulated in memory and written only after all selected data sources succeed, preventing partial sections.
- Requests use a dedicated session with proxy-environment handling disabled, timeouts, redirect rejection, response-size limits, and JSON-object validation.
- Pipe and physical newline characters are normalized in item identifiers used by `sep(124)` sections.

## Masking-view cache

The expensive masking-view walk is cached below `$OMD_ROOT/tmp` using a filename derived from a SHA-256 digest of the target host.

- Cache content is structured JSON, not executable or raw agent output.
- Cache files must be regular files and may not be symlinks.
- Cache size is bounded.
- Writes use a same-directory temporary file, `fsync`, mode `0600`, and atomic `os.replace`.
- Invalid caches fail visibly instead of silently returning partial or corrupt data.
- There is no worker pool; individual request failures can no longer disappear inside a thread while incomplete results are cached.

## Configuration

Rule: **Setup → Agents → Other integrations → Unisphere PowerMax**

| Parameter | Default | Meaning |
| --- | --- | --- |
| `username` / `password` | required | Unisphere API credentials; the password remains a Checkmk secret. |
| `port` | `8443` | HTTPS port. |
| `api_version` | `100` | Unisphere REST API namespace. |
| `use_ip` | off | Use the Checkmk host's primary IP instead of its name. |
| `cache_time` | `30 min` | Masking-view cache lifetime, constrained by the runtime. |
| `no_cert_check` | off | Disable certificate validation for legacy installations. Use only during migration. |
| `enable_remote_sym_checks` | off | Include remote Symmetrix systems. |
| `disable_get_*` | off | Disable individual data sources. |

## Sections

The existing section names and JSON payload shapes remain available:

- `unisphere_powermax_srp`
- `unisphere_powermax_director`
- `unisphere_powermax_health_score`
- `unisphere_powermax_health_check`
- `unisphere_powermax_array_performance`
- `unisphere_powermax_port_group`
- `unisphere_powermax_alerts`
- `unisphere_powermax_volume`
- `unisphere_powermax_port`

## Failure behavior

A selected data source is no longer skipped after an exception. Any failed selected source returns a non-zero agent result with no partial stdout. Operators can disable a source explicitly in the rule when a target Unisphere version does not implement it.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/unisphere_powermax/libexec/agent_unisphere_powermax` | Deterministic API collector and atomic cache implementation. |
| `src/unisphere_powermax/server_side_calls/unisphere_powermax.py` | Secret-aware command wiring. |
| `src/unisphere_powermax/rulesets/rulesets.py` | Special-agent and check-parameter rules. |
| `src/unisphere_powermax/agent_based/` | Existing section parsers and checks. |
| `tests/test_runtime_safety.py` | Synthetic-failure, cache and failure-propagation regression tests. |
