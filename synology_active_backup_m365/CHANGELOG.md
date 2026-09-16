# Changelog

## 0.1.0 - 2026-09-17

- Add the initial `synology_active_backup_m365` package framework.
- Document the Synology DSM collector installation as the first acceptance step.
- Pin the initial collector baseline to upstream release `v0.2.6-58b6a82-7.1`.
- Add a Checkmk 2.5 special agent using the Password Store reference mechanism for the API token.
- Add parsing, permanent health discovery, and stable per-task discovery based on `task_id`.
- Validate the collector API against a live Active Backup for Microsoft 365 payload.
- Treat global collector health as multi-product state and ignore unrelated missing ABB/Hyper Backup databases for the M365 Health service.
- Confirm the live M365 mapping `status=2`, `raw_status=6` as Warning and retain the vendor `error_code` as diagnostic data without assigning an undocumented meaning.
- Add independent last-fully-successful-backup age evaluation with daily-backup defaults of WARN after 30 hours and CRIT after 48 hours.
- Add graphing definitions for collector age, latest-run age, last-success age, runtime, and transferred bytes.
- Add sanitized regression fixtures for both the initial multi-product payload with unrelated ABB missing and the final clean M365-only collector state with `health.ok=true`.
- Confirm that disabling unused Active Backup for Business collection and restarting the DSM package removes ABB from `db_missing`/`sources` without changing the M365 task identity or job schema.
- Add architecture, security, testing, third-party dependency documentation, and sanitized API fixtures.

This version remains an integration/acceptance release until the transport is production-hardened and the final missing-job policy has been validated.
