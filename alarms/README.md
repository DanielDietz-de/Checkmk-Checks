# Alarms

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Notification plugin that plays an audible alarm through an HTTP API backend, for example to signal incidents on a TV, workstation or dedicated alarm box. Tested against a simple PHP backend shipped with XAMPP on Windows 11.

## How it works

On each notification, the script in `notifications/alarms` checks `NOTIFY_WHAT == SERVICE` and only fires when `NOTIFY_SERVICESTATE` is not `OK`. It then performs a `GET` against `{proto}://{hostname}/{url}?alarm={file}.mp3`, where the selected alarm name is mapped to a filename (`alarm1` -> `alarm-1.mp3`, `alarm2` -> `alarm-2.mp3`, `alarm3` -> `alarm-3.mp3`, `alarm4` -> `alarm-4.mp3`, `horse` -> `horse.mp3`). Exit code 0 on HTTP 200, 1 otherwise.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/alarms` | The notification script executed by Checkmk. |
| `src/alarms/rulesets/alarms.py` | WATO form for the notification parameters. |

## Installation

1. Deploy the HTTP backend that accepts the `?alarm=<file>` query parameter and plays the corresponding audio file on the target host (for example XAMPP on Windows 11 with a small PHP handler).
2. Install the MKP on the Checkmk site.
3. Create a notification rule that uses the `Play alarms (using API)` method and fill in the parameters below.

## Configuration

Rule: **Setup → Events → Notifications → Parameters for selected notification method → Play alarms (using API)**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `proto` | Choice (`http`, `https`) | Protocol used to reach the backend. Default `http`. |
| `hostname` | String | Host running the alarm backend. Default `localhost`. |
| `url` | String | Path of the API on the backend. Default `api.php`. |
| `alarm` | Choice (`alarm1`..`alarm4`, `horse`) | Which sound file to play. |

## Known limitations

- Only reacts to service notifications (`NOTIFY_WHAT == SERVICE`); host notifications are ignored.
- Sound filenames are hardcoded in the script; adding new entries requires editing both the ruleset and `notifications/alarms`.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `alarms` version `2.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `alarms/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `alarms-1.0.0.mkp`, `alarms-2.0.0.mkp`, `alarms-2.1.0.mkp`, `alarms-2.1.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/alarms/rulesets/alarms.py`.
- **Notifications:** `src/notifications/alarms`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_alarms_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
