# EC Cleanup Script

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p13-blue)
<!-- compatibility-badges:end -->

Command-line helper for the Checkmk Event Console. It finds open Event Console events whose corresponding Checkmk host or service is already back to OK and can archive exactly those events.

The command is read-only by default. Event deletion requires both `--execute` and either an exact interactive confirmation or the explicit `--yes` flag.

## How it works

1. List open Event Console events filtered by the supplied `event_rule_id`.
2. Query the current Checkmk state of the matching host or service.
3. Print every event as `OK`, `ACTIVE`, or `NOT FOUND`.
4. Build an in-memory list of only the events whose current state is OK.
5. In the default dry-run mode, print the candidate count and exit without changing the Event Console.
6. With `--execute`, require the operator to type `DELETE <count>` before archiving the listed events. `--yes` is available for deliberate non-interactive execution.
7. Validate every API response and return a non-zero exit code if an archive request fails.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/bin/sync_ec_events.py` | Safe Event Console reconciliation tool installed into the site `bin/` directory. |
| `tests/test_sync_ec_events.py` | Regression tests for dry-run, confirmation, and credential-boundary behavior. |

## Installation

1. Install the MKP on the Checkmk site.
2. Log in as the site user.
3. Run a dry run first:

```text
sync_ec_events.py --rule-filter <rule_id>
```

4. Review the listed candidates.
5. Execute the cleanup only after review:

```text
sync_ec_events.py --rule-filter <rule_id> --execute
```

For non-interactive execution after an equivalent review process:

```text
sync_ec_events.py --rule-filter <rule_id> --execute --yes
```

## Usage

```text
sync_ec_events.py --rule-filter <rule_id> [--execute] [--yes] \
                  [--user <name> --password <secret>] \
                  [--site-url https://host/site] [--timeout 15] [--no-verify]
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `--rule-filter` | yes | Event Console rule ID whose open events should be reconciled. |
| `--execute` | no | Enable event archival. Without this flag, no Event Console data is changed. |
| `--yes` | no | Skip the exact confirmation prompt. Requires `--execute`. |
| `--user` / `--password` | no | Explicit Checkmk API credentials. They must be supplied together. |
| `--site-url` | no | Full site URL. Defaults to `http://localhost/<OMD_SITE>`. |
| `--timeout` | no | API timeout in seconds. Default: 15. |
| `--no-verify` | no | Disable TLS certificate verification for an explicitly configured remote site URL. |

When credentials are not supplied, the script uses the local `automation` user and reads the site automation secret from `${OMD_ROOT}/var/check_mk/web/automation/automation.secret`. In that mode, the target is strictly limited to the current site on `localhost` or a numeric loopback address. A remote `--site-url` requires explicit `--user` and `--password` values; the local automation secret is never sent to it. Proxy environment variables are ignored when local automation credentials are used.

## Safety properties

- No hard-coded event ID or site ID.
- Dry-run behavior is the default.
- Exact event count must be confirmed before deletion.
- Only events verified as currently OK are candidates.
- API errors are never interpreted as OK.
- Host names are URL-encoded before use in REST paths.
- HTTP requests use a configurable timeout.
- Local automation credentials cannot leave the current site or loopback interface.
