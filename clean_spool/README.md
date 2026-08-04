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

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `clean_spool` version `1.0.3`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `clean_spool/src/info`; it declares 1 packaged files.
- Repository MKP artifacts present: `clean_spool-1.0.0.mkp`, `clean_spool-1.0.1.mkp`, `clean_spool-1.0.2.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Other packaged source:** `src/bin/clean_spoolfiles`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_parser.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
