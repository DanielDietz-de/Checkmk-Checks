# Testing

## Acceptance sequence

Testing is intentionally split so failures can be isolated to the Synology collector, transport/API layer, or Checkmk layer.

### Stage A — Synology collector

**Status: completed on 2026-09-17 against the representative M365 NAS.**

Validated evidence:

- anonymous `/api/v1/status` returns `401 Unauthorized`;
- authenticated `/api/v1/ping` returns `{"ok":true}`;
- authenticated `/api/v1/status` returns valid `health`, `jobs`, and `sources` objects;
- the Microsoft 365 SQLite source reports `found: true`;
- M365 discovery returns stable `task_id` values;
- normalized `status=2` / `raw_status=6` is observed as Warning;
- `last_success_age_seconds`, runtime, latest-run age, and transferred bytes are populated;
- the upstream global health object becomes false when an unrelated enabled ABB database is missing;
- after disabling unused Active Backup for Business and restarting the DSM package, the collector reports only the M365 source and `health.ok=true` while preserving the same M365 task identity and schema.

Two sanitized live regression fixtures cover both source-side states:

- `status_live_warning_unrelated_abb_missing.json` — M365 healthy but global health false because unused ABB is still enabled;
- `status_live_m365_only_warning.json` — final M365-only configuration with `health.ok=true`.

Do not commit raw production API output. Create or update sanitized fixtures instead.

### Stage B — Special agent

After the Checkmk package is installed, manual execution as the site user will be tested with the explicit token option:

```bash
~/local/lib/python3/cmk_addons/plugins/synology_active_backup_m365/libexec/agent_synology_active_backup_m365 \
  --host NAS_IP \
  --port 9876 \
  --token 'TEST_TOKEN'
```

Expected output starts with:

```text
<<<synology_active_backup_m365:sep(0)>>>
```

followed by one compact JSON object.

The token must never appear in stdout/stderr.

### Stage C — Checkmk registration and discovery

Planned commands:

```bash
cmk -D <nas-host>
cmk -d <nas-host>
cmk -vII <nas-host>
cmk -nv <nas-host>
```

Expected services:

```text
Synology M365 Backup Health
Synology M365 Backup <task_id>
```

## Fixture scenarios

The framework includes sanitized fixtures and is intended to cover:

- healthy successful job;
- healthy M365 source with a warning/partial job;
- unrelated ABB database missing while M365 remains healthy;
- running job;
- failed job;
- no data;
- unknown status;
- M365 database/source missing;
- collector unhealthy;
- stale collection;
- empty jobs;
- malformed JSON;
- missing required top-level keys;
- HTTP 401/403/500;
- timeout/refused connection;
- renamed job with unchanged task ID;
- deleted/missing expected job.

## Repository validation

Package tests use source-contract and sanitized-fixture tests that do not require access to the production NAS. Before release, the package is also run through the repository's deterministic MKP build, security guard, package tests, and clean-site Checkmk 2.5 validation workflows.
