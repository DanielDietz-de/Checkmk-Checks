# Testing

## Acceptance sequence

Testing is intentionally split so failures can be isolated to the Synology collector, transport/API layer, or Checkmk layer.

### Stage A — Synology collector

Follow the first section of [`../README.md`](../README.md).

Required evidence:

- package architecture and version;
- `401 Unauthorized` without a token;
- successful authenticated `/api/v1/ping`;
- successful `/api/v1/status` JSON;
- an M365 source with `found: true`;
- representative M365 job entries matching the DSM UI.

Do not commit production API output. Create or update sanitized fixtures instead.

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

The framework starts with sanitized fixtures and will expand to cover:

- healthy successful job;
- running job;
- warning/partial/skipped job;
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

Once the live schema is accepted, package tests must include source-contract tests that do not require access to the production NAS. Before release, the package will also be run through the repository's normal deterministic MKP and Checkmk 2.5 validation workflows.
