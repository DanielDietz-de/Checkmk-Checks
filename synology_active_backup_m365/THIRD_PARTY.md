# Third-party components

## Synology Active Backup Zabbix Monitor

This Checkmk integration consumes the JSON API exposed by the independent project:

- Project: https://github.com/pthoelken/synology-activebackup-zabbixmonitor
- License: MIT
- Initial integration baseline: `v0.2.6-58b6a82-7.1`
- Baseline release date: 2026-09-15
- Baseline commit: `58b6a820088d8058512fd5428e9f0c9deb825d14`

The collector is **not vendored** into this repository and its SPK files are not redistributed by this package. Administrators download the appropriate release artifact directly from the upstream GitHub release and install it manually through Synology DSM Package Center.

The upstream collector provides the Synology-specific functionality that this project intentionally does not duplicate:

- read-only access to the Active Backup for Microsoft 365 SQLite data;
- DSM package lifecycle and package-user execution;
- M365 task normalization;
- collector cache and health information;
- token-protected JSON endpoints including `/api/v1/status`.

The Checkmk integration owns only the monitoring-facing contract: API retrieval, validation, Checkmk discovery, service state evaluation, metrics, configuration rules, and packaging.

When upgrading the upstream collector, validate its API schema and status semantics against this integration before production rollout.
