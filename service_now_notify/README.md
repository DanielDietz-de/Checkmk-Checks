# ServiceNow notification

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Notification plug-in that creates and closes ServiceNow incidents through a customer middleware endpoint. Checkmk contact groups determine the default assignment group, while host and service attributes can override it.

## Transport and delivery safety

- The configured API value must be an absolute HTTPS base URL.
- Both problem and recovery endpoints are built from the same normalized base URL.
- Basic authentication is therefore never sent over cleartext HTTP.
- Redirects and proxy-environment variables are disabled.
- An optional proxy must itself be an absolute HTTPS URL without embedded credentials.
- TLS uses the system trust store or an optional private CA bundle.
- Requests have a configurable timeout and responses are capped at 1 MiB.
- Every 2xx status is accepted; non-2xx responses and invalid JSON fail the notification without copying the response body into logs or monitoring output.
- Create and close POSTs are attempted once. An ambiguous timeout is not retried because the middleware may already have applied the operation.
- The previous persistent DEBUG log containing complete payloads and responses was removed.

## Endpoints

For an API base such as:

```text
https://middleware.example/api/
```

the plug-in calls:

```text
https://middleware.example/api/checkmk/incident/create
https://middleware.example/api/checkmk/incident/close
```

A trailing slash is added safely when omitted.

## Assignment behavior

The default is `SNOW_000_OS`. Contact groups matching `SNOW_<number>...` are parsed defensively, and the numerically highest valid group wins. Malformed names are ignored rather than raising an exception.

Overrides:

- host: `HOST_SNOW_RESP_GRP`;
- service: `SERVICE_SNOW_RESP_GRP_2`;
- the historical duplicated key `SERVICE_SVC_SNOW_RESP_GRP_2` remains accepted for migration.

All values copied from notification context into the payload are bounded and stripped of control characters.

## On-call duty labels

The following service labels can force the service level to `0` (`Keine_Bereitschaft`):

| Label set to `OFF` | Effect |
| --- | --- |
| `SNOW_onCALLDUTY_WARN` | WARN only. |
| `SNOW_onCALLDUTY_CRIT` | CRIT only. |
| `SNOW_onCALLDUTY_ALL` | WARN and CRIT. |

## Configuration

| Parameter | Meaning |
| --- | --- |
| `api_url` | Absolute HTTPS API base URL. |
| `api_user` | Basic-authentication user. |
| `api_password` | Basic-authentication password stored as a Checkmk secret. |
| `timeout` | Per-request timeout, constrained to 0.5–120 seconds. |
| `ca_bundle` | Optional absolute private CA bundle. |
| `proxy` | Optional absolute HTTPS proxy without embedded credentials. |

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/service_now_notify` | Payload creation, secure delivery and response validation. |
| `src/service_now_notify/rulesets/service_now_notify.py` | Notification parameters. |
| `tests/test_service_now_notify.py` | URL, retry, assignment and recovery regression tests. |

The middleware payload field names remain customer-specific (`QUELLE`, `ZIEL`, `KURZBESCHREIBUNG`, and so on). `DISPOSITION` currently maps service level `0` to `Keine_Bereitschaft` and `10` to `Bereitschaft`; other values become `N/A`.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `service_now_notify` version `2.2.0`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `service_now_notify/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `service_now_notify-2.0.21.mkp`, `service_now_notify-2.1.0.mkp`, `service_now_notify-2.1.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/service_now_notify/rulesets/service_now_notify.py`.
- **Notifications:** `src/notifications/service_now_notify`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_service_now_notify.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- The notification obtains its credential from the Checkmk notification context or environment at runtime; no credential is stored in package source or generated documentation.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
