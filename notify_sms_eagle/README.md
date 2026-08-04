# SMS Eagle Notification

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Checkmk notification plugin that sends host/service alerts as SMS via
an SMS Eagle appliance using its v2 HTTP API and token authentication.
Optionally includes a configured host or service label in the SMS
text.

## How it works

The notification script `sms_eagle` is invoked by Checkmk with the
usual notification context. It POSTs a JSON payload to
`<api_host>/api/v2/messages/sms_single` with the `access-token` header:

```text
{"to": "<CONTACTPAGER>", "text": "<hostname> [SL key:value] [HL key:value] <state> <output>"}
```

The message is built from the host name, an optional matching
service/host label, and the current host or service state plus output,
truncated to 160 characters.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/sms_eagle` | Notification script (Python, uses `requests`). |
| `src/sms_eagle/rulesets/notification_parameter.py` | Registers notification parameter `sms_eagle` via `notification_parameter_registry`. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a notification rule in *Setup -> Notifications* and pick
   *SMS Eagle SMS Appliance* as the method.
3. Supply an API token created on the SMS Eagle appliance.

## Configuration

Notification parameters (`sms_eagle`):

| Parameter | Type | Meaning |
| --- | --- | --- |
| `api_host` | String | Base URL of the SMS Eagle API, e.g. `https://eagle.example.com`. |
| `api_token` | Password | v2 API access token. |
| `svc_label` | String (optional) | Service label key whose value will be embedded in the SMS. |
| `host_label` | String (optional) | Host label key whose value will be embedded in the SMS. |
| `ssl_verify` | BooleanChoice (default: true) | Verify the appliance TLS certificate. Prefer a private CA; disable only as a temporary diagnostic exception. |
| `allow_insecure_http` | BooleanChoice (default: false) | Permit clear-text HTTP to a remote appliance. Keep disabled for credential-bearing traffic. |

The recipient's phone number is taken from the Checkmk contact's
pager address (`CONTACTPAGER`). If empty, the plugin exits with state
2.

## Security and operational limits

- HTTPS is required for remote appliances unless `allow_insecure_http` is explicitly enabled.
- TLS verification is enabled by default; no global warning suppression is used.
- Authenticated redirects and inherited proxy settings are disabled to prevent token leakage across trust boundaries.
- Responses are read with a strict size limit and request timeouts are bounded.
- SMS text remains limited to 160 characters.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `notify_sms_eagle` version `2.3.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `notify_sms_eagle/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `notify_sms_eagle-1.0.0.mkp`, `notify_sms_eagle-2.0.0.mkp`, `notify_sms_eagle-2.1.0.mkp`, `notify_sms_eagle-2.1.2.mkp`, `notify_sms_eagle-2.1.3.mkp`, `notify_sms_eagle-2.1.4.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/sms_eagle/rulesets/notification_parameter.py`.
- **Notifications:** `src/notifications/sms_eagle`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_notify_sms_eagle_integrity.py`, `tests/test_notify_sms_eagle_transport_boundary.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- The notification obtains its credential from the Checkmk notification context or environment at runtime; no credential is stored in package source or generated documentation.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
