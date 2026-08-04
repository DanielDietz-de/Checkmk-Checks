# Asterisk notification script

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Notification script that places a phone call via an Asterisk PBX when Checkmk raises a notification. Uses the Asterisk Manager Interface (AMI) `Originate` action to dial a configured channel / extension.

## How it works

The script [`notifications/asterisk`](src/notifications/asterisk) collects the notification context, logs in to the AMI endpoint with `asterisk.ami.AMIClient`, issues an `Originate` action with the configured channel, extension, context, priority and caller ID, and then logs off. If the Python package `asterisk-ami` is missing the script exits with a clear error.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/asterisk` | Notification script invoked by Checkmk. |
| `src/asterisk/rulesets/asterisk.py` | WATO notification parameter form (legacy `cmk.gui.plugins.wato` API). |

## Installation

1. Install the MKP on the Checkmk site.
2. As the site user, install the required Python package: `pip3 install "asterisk-ami>=0.1.7"`.
3. In Checkmk create a notification rule using *Asterisk* and fill in the parameters below.

## Configuration

Rule: **Setup -> Notifications -> Notification rule -> Notification Method: Asterisk**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `host` | Text | IP address of the Asterisk server. |
| `port` | Integer | AMI port (default `5038`). |
| `timeout` | Integer | AMI timeout in seconds (default `180`, must exceed expected call duration). |
| `username` | Text | AMI user with `call`, `command` and `originate` privileges. |
| `password` | Password | AMI password (individual or stored). |
| `channel` | Text | Channel used for calling (e.g. `SIP/trunk`). |
| `exten` | Text | Extension to dial. |
| `priority` | Integer | Dialplan priority (default `1`). |
| `context` | Text | Dialplan context. |
| `callerid` | Text | Caller ID used for the outgoing call. |

## Known limitations

- The ruleset uses the pre-2.3 `notification_parameter_registry` API; it still loads on 2.3 / 2.4 as long as the legacy API is available.
- The script sends a call only, it does not speak the notification content; pairing it with a dialplan that plays a message is up to the Asterisk side.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `asterisk` version `2.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `asterisk/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `asterisk-1.0.0.mkp`, `asterisk-2.0.0.mkp`, `asterisk-2.1.0.mkp`, `asterisk-2.1.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/asterisk/rulesets/asterisk.py`.
- **Notifications:** `src/notifications/asterisk`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_asterisk_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- The notification handles a credential at runtime. Verify its retrieval and logging boundary in the notification source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
