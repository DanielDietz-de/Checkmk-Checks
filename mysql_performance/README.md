# Mysql Performance Checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Adds a MySQL Thread Cache hit-rate subcheck on top of the built-in
Checkmk MySQL monitoring. No extra agent plugin is required — the stock
`mk_mysql` section is consumed directly.

## How it works

The check plugin reads `Threads_created` and `Connections` from the
`mysql` section and computes the Thread Cache hit rate as
`(Threads_created / Connections) * 100`. One service
`MySQL <instance> Thread Cache` is discovered per MySQL instance.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agent_based/mysql_performance.py` | Check plugin on the legacy `agent_based_api.v1` register API. |
| `src/web/plugins/wato/mysql.py` | WATO ruleset `mysql_tchitrate`. |

## Installation

1. Install the MKP.
2. Deploy `mk_mysql` on the MySQL hosts.
3. Run service discovery.

## Services & metrics

- **Service:** `MySQL <instance> Thread Cache`
- **Metric:** `percent` — thread-cache hit rate in %.
- **State logic:** WARN at >=80, CRIT at >=90 (currently hardcoded in
  the check function).

## Known limitations

- The check plugin still uses the pre-2.3 `agent_based_api.v1` register
  API (`from .agent_based_api.v1 import register`).
- The WATO file uses the legacy `register_check_parameters` API.
- WARN/CRIT levels are currently hardcoded to 80/90 in the check function. The ruleset exposes configurable levels, but the check implementation does not consume them yet.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `mysql_performance` version `2.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `mysql_performance/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `mysql_performance-1.0.0.mkp`, `mysql_performance-1.0.1.mkp`, `mysql_performance-1.0.5.mkp`, `mysql_performance-1.0.mkp`, `mysql_performance-2.0.0.mkp`, `mysql_performance-2.1.0.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/mysql_performance/agent_based/mysql_performance.py`.
- **Rulesets:** `src/mysql_performance/rulesets/mysql_tchitrate.py`.
- **Check manuals:** `src/mysql_performance/checkman/mysql_performance`.
- Registered check plug-in names: `mysql_performance`.

### Validation

- Package-specific tests: `tests/test_mysql_performance_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
