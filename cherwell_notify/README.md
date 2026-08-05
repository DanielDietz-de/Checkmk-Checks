# Cherwell notification script

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

Notification script that creates incidents in Ivanti Service Management (formerly Cherwell) and can acknowledge a related Checkmk Event Console problem with the returned incident number.

## Security and lifecycle behavior

- Cherwell token and incident URLs must be absolute HTTPS URLs.
- TLS certificate verification is always enabled. Private certificate authorities can be supplied through CA bundle paths.
- Proxy environment variables are ignored for requests carrying Cherwell or Checkmk credentials.
- Redirects are rejected rather than forwarding credentials to another endpoint.
- OAuth tokens are requested for the current notification and are not written to disk.
- The Checkmk REST API also uses verified HTTPS and a configurable private CA bundle.
- Event Console acknowledgement uses only the REST API. The legacy event-daemon socket fallback was removed.
- Event IDs and host names are URL-encoded before use in links or REST paths.
- API errors, invalid JSON, missing incident IDs, and unexpected redirects return a non-zero notification result.

## Tenant configuration

No business object, customer, service, origin, or status identifiers are built into the code. Configure:

- `business_object_id`: the incident `busObId` for the target tenant;
- `description_field_id`: the field receiving the generated Checkmk description;
- `insert_fields_json`: additional static fields for incident creation;
- `update_fields_json`: optional fields for the post-create update;
- `cache_scope`: the Cherwell cache scope, normally `Tenant`.

Field lists use JSON such as:

```json
[
  {
    "fieldId": "BO:...FI:...",
    "value": "Checkmk",
    "dirty": true
  }
]
```

At most 100 fields are accepted in each list. Values are limited and normalized to strings.

## Notification behavior

### Problems

1. Request an OAuth token.
2. Create an incident using the configured business object and fields.
3. Optionally apply the configured update fields.
4. For Event Console problems, acknowledge the event with the incident number.

If Event Console acknowledgement fails, the notification fails visibly; it does not inject a command into the event daemon socket.

### Recoveries

Choose one explicit recovery mode:

- `ignore`: return successfully without contacting Cherwell;
- `create`: create a separate recovery incident using the same configured field mappings and a description identifying the notification as a recovery.

The integration does not claim to close the original incident because no reliable incident correlation identifier is available in a generic Checkmk recovery context.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `api_url` | Absolute HTTPS Cherwell business-object endpoint. |
| `token_url` | Absolute HTTPS OAuth token endpoint. |
| `client_id` | OAuth client ID. |
| `username` / `password` | Cherwell API credentials. |
| `business_object_id` | Tenant-specific incident business-object ID. |
| `description_field_id` | Tenant-specific description field ID. |
| `insert_fields_json` | Additional incident creation fields. |
| `update_fields_json` | Optional post-create fields; `[]` disables the second request. |
| `cache_scope` | Cherwell cache scope. |
| `recovery_mode` | `ignore` or `create`. |
| `ca_bundle` | Optional absolute private CA bundle for Cherwell. |
| `timeout` | Per-request timeout, constrained to 0.5–120 seconds. |
| `automation_secret` | Checkmk automation secret used only for EC acknowledgement. |
| `cmk_server` | Checkmk hostname with optional port, without scheme or path. |
| `cmk_site` | Checkmk site name. |
| `cmk_ca_bundle` | Optional absolute private CA bundle for Checkmk. |

## Migration from 2.0.x

Version 2.1.0 removes tenant-specific constants from the source. Existing rules must supply the business-object ID, description field ID, and any required insert/update field mappings before activation.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/cherwell_notify` | Notification runtime. |
| `src/cherwell_notify/rulesets/cherwell_notify.py` | Notification parameter form. |
| `tests/test_cherwell_notify.py` | TLS, recovery, field mapping, and initialization regression tests. |

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cherwell_notify` version `2.1.0`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cherwell_notify/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `cherwell_notify-2.0.0.mkp`, `cherwell_notify-2.0.1.mkp`, `cherwell_notify-2.0.2.mkp`, `cherwell_notify-2.0.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/cherwell_notify/rulesets/cherwell_notify.py`.
- **Notifications:** `src/notifications/cherwell_notify`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_cherwell_notify.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- The notification obtains its credential from the Checkmk notification context or environment at runtime; no credential is stored in package source or generated documentation.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
