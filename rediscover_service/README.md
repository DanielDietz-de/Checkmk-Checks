# Rediscover service

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p5-blue)
<!-- compatibility-badges:end -->

Notification plug-in that triggers a service rediscovery through the Checkmk REST API when a matching service notification fires.

## Security model

The notification reads the executing site's local `automation` secret. The configured protocol, hostname, and site name are validated before that secret is read:

- only HTTP or HTTPS is accepted;
- the hostname must be `localhost`, a `127.0.0.0/8` address, or `::1`;
- the configured site name must equal the current `OMD_SITE`;
- proxy-environment handling is disabled for API requests.

The local automation credential can therefore never be sent to a remote host or another local Checkmk site. Distributed or remote-site rediscovery requires a different design with explicitly configured, scoped credentials.

## How it works

1. Validate that the target is the executing site through a loopback address.
2. Read the local automation secret.
3. Look up the affected service in the discovery table.
4. Move the service to `undecided` and then back to `monitored` using the returned discovery parameters.
5. Activate the resulting change.

The plug-in only runs for service notifications. Host notifications are ignored.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/notifications/rediscover_service` | Notification script with local-site credential confinement. |
| `src/redis_service/rulesets/redis_service.py` | Notification parameter form. |
| `tests/test_local_target.py` | Regression tests for the local credential boundary. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a notification rule and select *Rediscover service*.
3. Configure the current site, normally with protocol `http`, hostname `localhost`, and the current site name.
4. Restrict the notification rule to the specific services that should be rediscovered.

## Configuration

| Parameter | Meaning |
| --- | --- |
| `proto` | HTTP or HTTPS for the local REST API. |
| `hostname` | `localhost` or a numeric loopback address. |
| `sitename` | Must match the executing `OMD_SITE`. |

## Remaining limitation

The current activation implementation still forces activation of pending changes. That behavior is addressed separately so the credential-boundary fix remains isolated.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `rediscover_service` version `2.0.5`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `rediscover_service/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `rediscover_service-1.0.1.mkp`, `rediscover_service-2.0.0.mkp`, `rediscover_service-2.0.1.mkp`, `rediscover_service-2.0.2.mkp`, `rediscover_service-2.0.3.mkp`, `rediscover_service-2.0.4.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Rulesets:** `src/redis_service/rulesets/redis_service.py`.
- **Notifications:** `src/notifications/rediscover_service`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_local_target.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- The source reads the local Checkmk automation secret. It must only transmit that credential to a validated loopback site URL.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
