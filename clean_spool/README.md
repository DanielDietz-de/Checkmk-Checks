# Clean spool files of Checkmk Notification Spooler

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p9-blue)
<!-- compatibility-badges:end -->

Helper script that identifies stale problem/recovery and downtime-start/downtime-end notification groups in the Checkmk notification spool and moves explicitly approved groups into a recoverable quarantine.

## Safety model

- Read-only dry run by default.
- `--execute` is required before any file is moved.
- Interactive execution requires the exact confirmation `MOVE <file-count>` unless `--yes` is supplied deliberately.
- Files newer than five minutes are ignored by default; adjust with `--min-age-seconds`.
- Only regular files are parsed. Symlinks and other filesystem objects are rejected.
- Every file is revalidated by device, inode, mtime, and size immediately before a group is moved.
- A non-blocking site-local lock prevents two cleanup processes from running together.
- Files are moved atomically to a timestamped quarantine directory on the same filesystem; they are not unlinked.
- If a group move fails partway through, already moved files are rolled back where possible and the command reports a non-zero status.
- Repeated problem or downtime-start notifications are retained in the plan instead of silently overwriting earlier records.

Spool records are parsed with bounded `ast.literal_eval`, never `eval`.

## Usage

Preview the plan:

```text
clean_spoolfiles
```

Execute with the default five-minute age threshold:

```text
clean_spoolfiles --execute
```

Non-interactive execution with a 15-minute age threshold:

```text
clean_spoolfiles --execute --yes --min-age-seconds 900
```

By default, files are moved from:

```text
$OMD_ROOT/var/check_mk/notify/spool
```

to a timestamped directory below:

```text
$OMD_ROOT/var/check_mk/notify/spool-cleanup
```

Use `--quarantine-dir` only for a directory on the same filesystem as the active spool.

## Pairing behavior

- Host state: all unmatched `PROBLEM` records followed by `RECOVERY`.
- Service state: all unmatched `PROBLEM` records followed by `RECOVERY`, keyed by `HOSTNAME###SERVICEDESC`.
- Host downtime: all unmatched `DOWNTIMESTART` records followed by `DOWNTIMEEND`.
- Service downtime: all unmatched `DOWNTIMESTART` records followed by `DOWNTIMEEND`.

Only complete groups are planned. Unmatched records stay in the active spool.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/bin/clean_spoolfiles` | Safe planning and quarantine command. |
| `tests/test_parser.py` | Non-executable parser regression tests. |
| `tests/test_cleanup_safety.py` | Dry-run, age, pairing, revalidation, and quarantine tests. |

## Recovery

Quarantined records remain available for operator review. To restore a record, stop or otherwise coordinate with the notification spooler, verify that the destination name is unused, and move the file back into the active spool as the Checkmk site user.
