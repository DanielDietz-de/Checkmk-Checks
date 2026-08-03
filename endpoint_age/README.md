# Public HTTPS endpoint freshness monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0-blue)
<!-- compatibility-badges:end -->

Checks whether content at a **public HTTPS endpoint** is still fresh. Each configured endpoint produces one `Endpoint age <name>` service and an `endpoint_age` metric.

## Security boundary

The special agent is deliberately not a general-purpose HTTP client:

- only absolute HTTPS URLs are accepted;
- URL credentials and fragments are rejected;
- DNS is resolved before the request and every returned address must be globally routable;
- loopback, private, link-local, reserved, multicast and otherwise non-public targets are rejected;
- redirects are rejected rather than followed to a second destination;
- environment proxies are ignored;
- TLS verification is mandatory;
- arbitrary request headers are not supported;
- each response is streamed and limited to 1 MiB;
- at most 100 endpoints may be configured;
- timeout values are restricted to 0.5–60 seconds.

These restrictions prevent a delegated Setup rule from using the monitoring server to access local services, cloud metadata endpoints, private APIs or local files. Internal and authenticated endpoints require a purpose-built integration with explicitly scoped credentials and an administrator-controlled destination policy.

## Freshness sources

- `age_header` — numeric `Age` response header.
- `date_header:<HeaderName>` — the named HTTP-date header, defaulting to `Last-Modified`.
- `json_path:<dotted.path>` — a bounded path such as `items[0].updated_at`; the selected scalar is interpreted as seconds or a supported date.

The JSON body must be valid UTF-8 JSON. Path length, header names, dates, result text and service names are bounded.

## Configuration

Rule: **Setup → Agents → Other integrations → Endpoint age (public HTTPS freshness)**

| Parameter | Meaning |
| --- | --- |
| `name` | Service item, 1–256 characters. |
| `url` | Public absolute HTTPS URL. |
| `source` | `age_header`, `date_header`, or `json_path`. |
| `timeout` | Per-endpoint timeout, 0.5–60 seconds. |

Rule: **Setup → Services → Service monitoring rules → Endpoint age** configures the maximum-age WARN/CRIT levels.

## Failure behavior

DNS failures, non-public addresses, redirects, TLS errors, non-2xx responses, oversized bodies, invalid JSON, missing paths and invalid freshness values are returned as a failed endpoint result. Response bodies and arbitrary remote exception details are not copied into agent output.

## Migration from 0.0.1

- HTTP URLs must be replaced by HTTPS URLs.
- Internal, loopback or private destinations are no longer supported.
- Saved `extra_headers` values are ignored and the field has been removed from Setup.
- Bearer tokens and API keys must not be embedded in URLs.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/endpoint_age/libexec/agent_endpoint_age` | Public HTTPS validation, bounded fetch and freshness extraction. |
| `src/endpoint_age/server_side_calls/agent.py` | Bounded special-agent command generation. |
| `src/endpoint_age/rulesets/agent.py` | Public-HTTPS-only endpoint configuration. |
| `src/endpoint_age/rulesets/endpoint_age.py` | WARN/CRIT age parameters. |
| `src/endpoint_age/agent_based/endpoint_age.py` | Parser, discovery and check. |
| `tests/test_http_boundary.py` | SSRF, header-removal and body-size regression tests. |

`Age` measures cache age, which is not always the underlying data age. Prefer a real producer timestamp through `json_path` when available.
