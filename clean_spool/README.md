# Clean spool files of Checkmk Notification Spooler

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p9-blue)
<!-- compatibility-badges:end -->

Helper script that cleans out stale notifications from the Checkmk notification spooler. When a notification outburst hits the spooler, recovery or downtime-end notifications can queue up behind problem or downtime-start notifications that will never be useful any more. This script scans the spool directory and deletes matching problem/recovery and downtime-start/downtime-end pairs so the spooler drains faster.

## How it works

The script reads every file in `$OMD_ROOT/var/check_mk/notify/spool`, orders them by mtime, and walks through them:

- For hosts: a `DOWNTIMESTART` paired with a later `DOWNTIMEEND` causes both files to be deleted; likewise a `PROBLEM` paired with a later `RECOVERY`.
- For services: the same logic keyed on `HOSTNAME###SERVICEDESC`.
- At the end it prints a small ASCII summary of how many host/service state and downtime entries were removed and the total number of files inspected.

Spool records are parsed with `ast.literal_eval`, never `eval`. Only dictionary records containing a dictionary `context` and the required string fields are accepted. Files larger than 1 MiB, malformed literals, executable expressions, and invalid schemas are skipped.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/bin/clean_spoolfiles` | Python script installed as `bin/clean_spoolfiles` in the site. |
| `tests/test_parser.py` | Regression tests for non-executable spool parsing. |

## Installation

1. Install the MKP on the Checkmk site.
2. Run `clean_spoolfiles` as the site user when the notification spooler is backed up. There is no scheduled trigger — you run it manually or wire it into a cron of your choice.

## Remaining operational limitations

- Matching spool files are still unlinked directly rather than quarantined.
- The command does not yet lock against a concurrently running notification spooler.
- The command is destructive by default.

Those deletion-safety concerns are handled in a separate change so this parser fix remains reviewable in isolation.
