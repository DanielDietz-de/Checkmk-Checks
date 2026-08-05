# BMC Helix Events notification

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Notification script that forwards Checkmk host and service events to BMC Helix Operations Management at `https://<portal>/events-service/api/v1.0/events`.

## Authentication

The integration uses the BMC Helix tenant API key directly:

```text
Authorization: apiKey <tenant-id>::<access-key>::<secret-key>
```

The rule stores the access and secret components as Checkmk passwords. No external `auth_api` module, JWT cache, or separate login request is required.

## Delivery safety

- The portal setting is a hostname with an optional port; schemes, paths, URL credentials, queries and fragments are rejected.
- Requests always use HTTPS with certificate validation through the system trust store or an optional private CA bundle.
- Redirects and proxy-environment handling are disabled for the credential-bearing request.
- Responses are streamed and limited to 1 MiB.
- HTTP and API-level failure responses return a non-zero notification result.
- Event-creation POST requests are attempted exactly once. A timeout can be ambiguous because BMC Helix may already have accepted the event, so retrying automatically could create a second event.
- Each event carries a stable `source_identifier` and `checkmk_id` derived from the full Checkmk host/service identity and problem ID. Configure the appropriate BMC Helix event-deduplication policy for the custom `checkmk_ev` class when repeated events should update rather than create.

## Payload

The event includes severity, message, source identifier, short hostname, Checkmk problem ID, service level, the first contact group ending in `_ALARM`, and the `anwendung` host label. Host `DOWN` maps to `CRITICAL`; host `UP` maps to `OK`.

For services, `source_identifier` is `<full-hostname>/<service-description>`. For hosts, it is the full Checkmk host name. `checkmk_id` uses `SERVICEPROBLEMID` or `HOSTPROBLEMID`, with a deterministic identity fallback when no problem ID is present.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/bhome_notify` | HTTPS client, event builder and response validation. |
| `src/bhome_notify/rulesets/notification_parameter.py` | BMC Helix tenant API-key configuration. |
| `tests/test_bhome_notify.py` | Authentication, single-attempt and payload regression tests. |

## Configuration

Rule: **Setup → Notifications → Notification method: BMC Helix Events API**

| Parameter | Meaning |
| --- | --- |
| `portal_domain` | BMC Helix portal hostname with optional port, without scheme or path. |
| `id` | Tenant ID component of the API key. |
| `access` | Access-key component stored as a Checkmk password. |
| `secret` | Secret-key component stored as a Checkmk password. |
| `timeout` | Per-request timeout, constrained to 0.5–120 seconds. |
| `ca_bundle` | Optional absolute private CA bundle; otherwise system trust is used. |

## Migration from 1.1.1

Remove any locally installed `auth_api` helper from the notification deployment after upgrading. Existing `id`, `access`, and `secret` rule values map directly to tenant ID, access key, and secret key; no credential conversion is required.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `bhome_notify` version `1.2.0`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `bhome_notify/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `bhome_notify-1.0.0.mkp`, `bhome_notify-1.1.0.mkp`, `bhome_notify-1.1.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/bhome_notify/rulesets/notification_parameter.py`.
- **Notifications:** `src/notifications/bhome_notify`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_bhome_notify.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- The notification obtains its credential from the Checkmk notification context or environment at runtime; no credential is stored in package source or generated documentation.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
