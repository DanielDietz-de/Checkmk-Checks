# Check for MySQL status variables

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p8-blue)
<!-- compatibility-badges:end -->

Exposes a wide set of `SHOW GLOBAL STATUS` variables as individual
Checkmk services on top of the stock MySQL agent section. No additional
agent plugin is required; this plugin works as a subcheck for the
normal Checkmk MySQL monitoring.

## How it works

The check plugin consumes the built-in `mysql` section. It iterates
over every MySQL instance in the section and emits one service per
variable listed in its inventory table. Counter variables are
converted to per-second rates via `get_rate()`, gauges are reported
verbatim, and boolean variables (e.g. `Slave_running`, `Compression`)
are compared against a configured target state.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/mysql_status/agent_based/mysql_status.py` | `CheckPlugin` `mysql_status` with inventory table mapping each variable to `Counter` / `Gauge` / `Boolean`. |
| `src/mysql_status/rulesets/mysql_status.py` | WATO ruleset `mysql_status` (upper levels and target state). |
| `src/mysql_status/graphing/mysql_status.py` | Metric definitions. |
| `src/mysql_status/checkman/mysql_status` | Check manual page. |

## Installation

1. Install the MKP.
2. Deploy `mk_mysql` on the MySQL hosts.
3. Run service discovery — one service per supported status variable
   per instance.

## Configuration

Rule: *Service monitoring rules -> Applications -> Settings for MySQL
status check* (ruleset `mysql_status`, per item).

| Parameter | Type | Meaning |
| --- | --- | --- |
| `levels` | Upper `SimpleLevels[Integer]` | Upper WARN/CRIT on the rate (Counter) or current value (Gauge). |
| `target_state` | SingleChoice `on` / `off` | Expected value for Boolean variables (e.g. `Slave_running`). |

## Services & metrics

- **Service:** `MySQL Status <instance> <variable>`
- **Metric:** `mysql_status_<variable_lowercase>`
- **Monitored variables:** `Aborted_clients`, `Aborted_connects`,
  `Bytes_received`, `Bytes_sent`, `Compression`, `Connections`,
  `Created_tmp_disk_tables`, `Created_tmp_files`, `Created_tmp_tables`,
  `Innodb_buffer_pool_pages_free`, `Innodb_buffer_pool_read_requests`,
  `Innodb_buffer_pool_reads`, `Innodb_buffer_pool_write_requests`,
  `Innodb_log_waits`, `Innodb_os_log_written`, `Innodb_row_lock_time`,
  `Innodb_row_lock_waits`, `Key_blocks_unused`, `Key_read_requests`,
  `Key_reads`, `Key_write_requests`, `Key_writes`, `Open_tables`,
  `Open_files`, `Qcache_free_memory`, `Qcache_free_blocks`,
  `Qcache_hits`, `Qcache_inserts`, `Qcache_low_mem_prunes`,
  `Qcache_lowmem_prunes`, `Qcache_not_cached`, `Queries`, `Questions`,
  `Select_full_join`, `Select_range_check`,
  `Slave_retried_transactions`, `Slave_running`, `Slow_launch_threads`,
  `Slow_queries`, `Sort_merge_passes`, `Table_locks_waited`,
  `Threads_cached`.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `mysql_status` version `6.3.2`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `mysql_status/src/info`; it declares 6 packaged files.
- Repository MKP artifacts present: `mysql_status-2.0.0.mkp`, `mysql_status-3.0.0.mkp`, `mysql_status-4.0.0.mkp`, `mysql_status-4.0.1.mkp`, `mysql_status-4.0.2.mkp`, `mysql_status-4.0.3.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/mysql_status/agent_based/mysql_status.py`.
- **Rulesets:** `src/mysql_status/rulesets/mysql_status.py`.
- **Graphing:** `src/mysql_status/graphing/mysql_status.py`.
- **Check manuals:** `src/mysql_status/checkman/mysql_innodb_buffer_pool_utilization`, `src/mysql_status/checkman/mysql_status`, `src/mysql_status/checkman/mysql_status_query_types`.
- Registered check plug-in names: `mysql_innodb_buffer_pool_utilization`, `mysql_status`, `mysql_status_query_types`.

### Validation

- Package-specific tests: `tests/test_mysql_status_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
