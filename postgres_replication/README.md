# PostgreSQL Replication

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Monitors PostgreSQL replication slots on a primary server. Creates one
Checkmk service per slot reporting the slot type, LSN, active flag, and
the lag in bytes relative to the current WAL position, with configurable
WARN/CRIT levels on the lag.

## How it works

1. Agent plugin [`postgres_replication.sh`](src/agents/plugins/postgres_replication.sh)
   runs on the PostgreSQL host as the `postgres` user via `su - postgres`.
2. It picks PostgreSQL 9 functions (`pg_xlog_location_diff`,
   `pg_last_xlog_receive_location`, `pg_current_xlog_location`) or the
   newer ones (`pg_wal_lsn_diff`, `pg_last_wal_receive_lsn`,
   `pg_current_wal_lsn`) based on `psql -V` major version.
3. It queries `pg_replication_slots` and prints one space-separated line
   per slot under `<<<postgres_replication>>>`:
   `slot_name slot_type slot_lsn delta active delta_pretty unit`.
4. The legacy check plugin parses the section, discovers one service per
   slot and reports slot type, LSN, active state and the byte lag.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/postgres_replication.sh` | Bash agent plugin running `psql` as `postgres` to dump replication slot state. |
| `src/agents/bakery/postgres_replication` | Legacy Bakery hook that deploys the shell plugin on Linux hosts. |
| `src/checks/postgres_replication` | Legacy check plugin `postgres_replication` with inventory and check function. |
| `src/web/plugins/wato/postgres_replication.py` | Legacy WATO rules: agent plug-in deployment and per-slot byte levels. |

## Installation

1. Install the MKP on the Checkmk site.
2. Deploy the agent plugin:
   - **With Bakery:** enable the rule *Agent Plugins -> Postgres
     Replication (Linux)*.
   - **Without Bakery:** copy
     `src/agents/plugins/postgres_replication.sh` into the agent's plugin
     directory and make it executable. The agent user must be able to
     `su - postgres` and run `psql`.
3. Run service discovery. One `PostgreSQL Replication <slot_name>` service
   is created per replication slot.

## Configuration

Rule: **Parameters for discovered services -> Applications -> PostgreSQL
Replication**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `levels` | `(warn, crit)` in bytes (`Filesize`) | Upper levels on the replication lag in bytes (`delta`). Default: 30 MiB / 60 MiB. |

## Services & metrics

- **Service:** `PostgreSQL Replication <slot_name>` - one per slot.
- **State logic:**
  - CRIT if the slot is not `active`.
  - WARN/CRIT from `check_levels` on the byte lag once it exceeds the
    configured levels.
- **Perfdata:** bytes used as the performance value.

## Known limitations

- Uses the legacy `check_info` / `register_rule` /
  `register_check_parameters` APIs and the legacy Bakery hook
  (`bakery_info[...]`), hence `min_required` 1.6.0. Still loads on modern
  Checkmk as long as the legacy APIs are available.
- Only slots with byte-valued deltas are evaluated; if `unit` is not
  `bytes`, no levels are applied.
- Runs `psql` via `su - postgres`, which may not work on setups with a
  different postgres shell or lockdown.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `postgres_replication` version `2.0.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `postgres_replication/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `postgres_replication-1.0.1.mkp`, `postgres_replication-1.0.2.mkp`, `postgres_replication-1.0.mkp`, `postgres_replication-1.1.0.mkp`, `postgres_replication-1.2.0.mkp`, `postgres_replication-1.2.1.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/postgres_replication/agent_based/postgres_replication.py`.
- **Rulesets:** `src/postgres_replication/rulesets/postgres_replication.py`.
- **Bakery:** `src/agents/bakery/postgres_replication`.
- **Check manuals:** `src/postgres_replication/checkman/postgres_replication`.
- **Other packaged source:** `src/agents/plugins/postgres_replication.sh`.
- Registered check plug-in names: `postgres_replication`.

### Validation

- Package-specific tests: `tests/test_postgres_replication_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- Emitted Checkmk sections detected in source: `postgres_replication`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
