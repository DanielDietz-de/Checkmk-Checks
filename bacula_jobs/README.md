# Bacula / Bareos Jobs Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Monitors Bacula or Bareos jobs by querying the catalog database directly on the Director host. One Checkmk service per job reports the latest state and backup age.

## Configuration security

Version 3.1 replaces the shell-sourced `bacula.cfg` with `$MK_CONFDIR/bacula_jobs.json`.

- The configuration is parsed as bounded JSON and is never executed.
- Database names, users, hosts, ports and timeouts are validated.
- Database clients are started with `subprocess.run()` argument arrays; no shell is invoked.
- The SQL statement is fixed in the plug-in and cannot be changed through the rule.
- Passwords are not written into the bakery configuration.
- MySQL credentials may be referenced through an existing absolute `0600` client defaults file.
- PostgreSQL credentials may be referenced through an existing absolute `0600` pgpass file.
- PostgreSQL peer authentication may optionally use a validated local operating-system account through `runuser --user ... -- psql`; no sudoers entry or shell command is generated.
- The process environment is reduced before database clients are executed.
- Query execution and output size are bounded.

The historical hard-coded `/root/.my.cnf` and `/etc/check_mk` paths have been removed.

## Agent Bakery

The package uses the current Checkmk Agent Bakery API. The bakery deploys:

- the Python agent plug-in `bacula_jobs`;
- a JSON configuration named `bacula_jobs.json`.

Existing historical `(deployment, config)` rule values are migrated as plain data. Legacy names such as `backend_type`, `dbname`, `dbuser`, and `dbhost` are translated without interpreting their contents as shell syntax.

## Configuration fields

Rule: **Setup → Agents → Agent rules → Bacula/Bareos jobs collector**

| Field | Meaning |
| --- | --- |
| `deployment` | Synchronous, cached, or not deployed. |
| `backend` | `mysql` or `postgresql`. |
| `database` | Catalog database name, default `bacula`. |
| `user` | Database user, default `bacula`. |
| `host` | Database host, default `localhost`. |
| `port` | Database port; use 3306 for MySQL or 5432 for PostgreSQL unless changed. |
| `timeout` | Database connection/query timeout, 1–120 seconds. |
| `mysql_defaults_file` | Optional protected MySQL client file. |
| `postgres_passfile` | Optional protected PostgreSQL pgpass file. |
| `postgres_os_user` | Optional local account for PostgreSQL peer authentication. |

Credential files must be absolute regular files, may not be symlinks, and must not be readable by group or others.

Example MySQL client file:

```ini
[client]
password=replace-me
```

Protect it on the monitored host:

```bash
chown root:root /etc/check_mk/bacula_mysql.cnf
chmod 0600 /etc/check_mk/bacula_mysql.cnf
```

Example manual JSON configuration:

```json
{
  "backend": "mysql",
  "database": "bacula",
  "user": "bacula_monitor",
  "host": "localhost",
  "port": 3306,
  "timeout": 15,
  "mysql_defaults_file": "/etc/check_mk/bacula_mysql.cnf"
}
```

## Query and output

The collector executes a fixed query for jobs whose `EndTime` is within the last 30 days and emits tab-separated rows below:

```text
<<<bacula_jobs:sep(9)>>>
```

The check keeps the newest row per job name. Jobs absent for more than 30 days can disappear from discovery; this behavior is unchanged.

## Service parameters

Rule: **Setup → Service monitoring rules → Bacula Jobs**

| Parameter | Meaning |
| --- | --- |
| `max_age` | WARN/CRIT thresholds for the latest job age; default 5/7 days. |
| `ok_states` | Bacula job states considered OK; default `T`, `R`. |
| `crit_states` | States considered CRIT; default `E`, `f`. |

States not present in either list become WARN.

## Migration from 3.0.x

1. Remove or archive `/etc/check_mk/bacula.cfg`; it is no longer read.
2. Do not place database passwords in the Bakery rule.
3. Create a protected MySQL defaults or PostgreSQL pgpass file where password authentication is required.
4. Configure the current Bakery rule and bake a new agent.
5. Remove obsolete sudoers permissions that allowed the old shell plug-in to execute `psql`.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/bacula_jobs` | JSON-based Python database collector. |
| `src/bacula_jobs/agent_based/bakery.py` | Current Agent Bakery deployment. |
| `src/bacula_jobs/rulesets/bakery.py` | Bakery configuration and legacy data migration. |
| `src/bacula_jobs/agent_based/bacula_jobs.py` | Parser, discovery and check. |
| `src/bacula_jobs/rulesets/bacula_jobs.py` | Job state and age parameters. |
| `tests/test_bacula_collector.py` | Configuration and command-execution security tests. |
