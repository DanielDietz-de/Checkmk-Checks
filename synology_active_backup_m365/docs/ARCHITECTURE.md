# Architecture

## Goal

Monitor Synology Active Backup for Microsoft 365 in Checkmk without reimplementing Synology's internal database discovery and normalization logic.

## Data flow

```text
Microsoft 365
    |
    v
Synology Active Backup for Microsoft 365
    |
    v
Synology SQLite data
    |
    v
pthoelken/synology-activebackup-zabbixmonitor
    |  read-only collector
    |  GET /api/v1/status
    v
Checkmk special agent
    |
    v
<<<synology_active_backup_m365:sep(0)>>>
    |
    +--> global health service
    +--> one service per stable task_id
```

## Responsibility boundary

### Upstream DSM collector

The external collector owns:

- locating and reading the Synology Active Backup databases;
- understanding the current Synology database schema;
- mapping raw M365 records into normalized jobs;
- collector/cache health;
- the DSM package lifecycle;
- the authenticated API.

### Checkmk integration

This repository owns:

- retrieving one complete status snapshot per Checkmk execution;
- authenticating without exposing the API token in the process list on Checkmk 2.5;
- validating the API response before emitting a Checkmk section;
- discovering the health service and M365 task services;
- evaluating Checkmk states;
- age/runtime/size metrics and future threshold rules;
- stale-data, missing-database, and missing-job policy;
- Checkmk MKP packaging and compatibility tests.

## API contract

The special agent consumes:

```text
GET /api/v1/status
Authorization: Bearer <token>
```

The response must be a JSON object with:

```text
health
jobs
sources
```

Only a single status request is performed per polling cycle. This avoids inconsistent service states caused by collecting health and individual jobs at different points in time.

## Service identity

The Synology `task_id` is the persistent Checkmk item.

The `job_name` is explicitly **not** used as the service identity because administrators can rename a task without creating a new underlying backup task. This keeps history and service configuration bound to the technical job rather than its display label.

## Initial state model

Normalized upstream statuses are currently interpreted conservatively:

| Upstream status | Meaning | Initial Checkmk state |
| ---: | --- | --- |
| `1` | OK | OK |
| `2` | Warning / partial / skipped | WARN |
| `3` | Running | OK |
| `6` | Failed | CRIT |
| `8` | No data | WARN |
| `9` | Database missing | CRIT |
| `10` | Unknown | UNKNOWN |

The real NAS acceptance payload is authoritative for finalizing edge cases.

## Health service

`Synology M365 Backup Health` exists independently of per-job discovery. It is intended to detect conditions that would otherwise cause services to disappear silently:

- collector not healthy;
- collector data stale;
- M365 data source/database absent;
- collector errors;
- no M365 jobs where jobs are expected.

A later production stage will add an explicit expected-job policy so deletion or accidental removal of a configured backup task can become a deterministic alert rather than only a discovery change.

## Network and trust boundaries

The upstream API is HTTP by default. The current acceptance flow therefore assumes a restricted management network and a DSM firewall rule limited to the Checkmk server/test host. Production deployment requires either a verified TLS path or an equivalently controlled transport boundary.

See [`SECURITY.md`](SECURITY.md).
