# Oxidized export

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p5-blue)
<!-- compatibility-badges:end -->

Exports the validated `oxidized_hosts` Checkmk view as a private JSON inventory for Oxidized.

## Security model

- The local automation secret may be sent only to the current Checkmk site through `localhost`, `127.0.0.0/8`, or `::1`.
- The default URL is `http://localhost/$OMD_SITE`; cleartext HTTP is never accepted for a non-loopback host.
- HTTPS uses the system trust store or an explicitly configured private CA bundle. Certificate verification cannot be disabled.
- Redirects and proxy environment variables are disabled for authenticated requests.
- The automation secret file must be a regular, non-symlink file with no group or other permissions.
- Responses are capped at 10 MiB and must contain a valid two-column view table.
- Every hostname and `[os]` tag is validated. Conflicting duplicate hosts fail the complete export.
- Output paths must remain below `OMD_ROOT` and may not be symlinks.
- Output is written atomically with mode `0640`.
- On any failed refresh, the active output is renamed to a timestamped `.stale.*` file so consumers cannot silently continue using an old active inventory.
- The exporter returns a non-zero status for request, validation, write, or scheduling failures.

## Output

The default output is:

```text
$OMD_ROOT/var/oxidized/oxidized.json
```

It is not published below `var/www/open`. Provide Oxidized with local filesystem access through an appropriately restricted account or expose the file through an authenticated service under your own access-control policy.

## Commands

Generate the inventory:

```text
export_oxidized export
```

Also print the generated JSON:

```text
export_oxidized export --stdout
```

Install or update the managed cron and logrotate configuration:

```text
export_oxidized install-schedule --interval-minutes 15
```

Remove the managed schedule:

```text
export_oxidized remove-schedule
```

`install-schedule` always rewrites the managed files using the current `OMD_ROOT`, `OMD_SITE`, output path, automation user, timeout, and CA bundle. It does not preserve stale hard-coded content from an earlier installation.

## Important options

| Option | Default | Meaning |
| --- | --- | --- |
| `--site-url` | `http://localhost/$OMD_SITE` | Current site on loopback only. |
| `--automation-user` | `oxidized` | Automation user used to read the view. |
| `--secret-file` | `$OMD_ROOT/var/check_mk/web/oxidized/automation.secret` | Restrictively permissioned automation secret. |
| `--output` | `$OMD_ROOT/var/oxidized/oxidized.json` | Private active inventory below `OMD_ROOT`. |
| `--timeout` | `15` | Per-request timeout, constrained to 0.5–120 seconds. |
| `--ca-bundle` | system trust | Optional absolute private CA bundle for HTTPS. |
| `--interval-minutes` | `15` | Schedule interval for `install-schedule`. |

## Checkmk view requirements

Create a view named `oxidized_hosts` with:

1. hostname in the first column;
2. an OS tag such as `[ios]`, `[junos]`, or `[picos]` in the second column.

Rows without a valid OS tag fail the export instead of creating a partial inventory.

## Migration from 1.0.x

- Remove any old file from `$OMD_ROOT/var/www/open/oxidized.json` after consumers are migrated.
- Run `export_oxidized install-schedule` to replace the old hard-coded cron and logrotate files.
- Configure Oxidized to read the new private output or an authenticated endpoint serving it.
- The historical `--cron` and `--dis-verify` flags are removed.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/bin/export_oxidized` | Export, schedule installation, and schedule removal command. |
| `tests/test_export_oxidized.py` | URL, parser, output, stale-state, permission, and path regression tests. |
