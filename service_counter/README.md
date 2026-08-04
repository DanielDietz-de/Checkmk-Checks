# Count pattern in services for metrics

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p14-blue)
<!-- compatibility-badges:end -->

Special agent that queries the local Checkmk REST API, counts how many existing services match one or more configurable filters (by service description, plugin output, host name / labels, site) and exposes each count as a local check with a `count` metric. Useful for building dashboards that show how many hosts or services are currently in a given state.

## How it works

1. The agent reads the site's automation secret and talks to
   `http://localhost:80/<site>/check_mk/api/1.0` as the `automation` user.
2. For every configured filter set it builds a Livestatus-style query
   (`/domain-types/service/collections/all`) combining the configured conditions with `and`:
   - `description = <name>`
   - `plugin_output ~ <pattern>`
   - `host_labels = '<key>' '<value>'` (optionally negated)
   - `host_name ~ <regex>`
   - `plugin_output = 'site' : '<sitename>'`
3. The number of returned services is emitted as a `<<<local>>>` section line:

   ```text
   <<<local>>>
   0 "Count Desc: Check_MK, Labels: env:prod" count=17 Found 17 times
   ```

4. Checkmk's built-in `local` check turns each line into a service with a `count` metric.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/service_counter/libexec/agent_service_counter` | Special agent that queries the REST API. |
| `src/service_counter/server_side_calls/service_counter.py` | Server-side call wiring. |
| `src/service_counter/rulesets/service_counter.py` | WATO rule with a list of filter sets and a timeout. |

## Installation

1. Install the MKP on the Checkmk site.
2. Attach the rule to a monitoring host that represents the Checkmk site (typically the site host itself).
3. Configure at least one filter set and run service discovery.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> Service counter**

Each entry in the *Service Definition* list may combine any of:

| Parameter | Type | Meaning |
| --- | --- | --- |
| `name` | String | Exact service description to match. |
| `service_pattern` | Regex | Substring/regex match against `plugin_output`. |
| `host_label_pattern` | `key:value[,key:value,...]` | All labels must be present on the host. |
| `host_label_pattern_negated` | `key:value[,...]` | None of these labels may be present. |
| `host_name_pattern` | Regex | Regex match on host name. |
| `site_name_pattern` | String | Filter by site name. |
| `timeout` | Time span | REST API request timeout (default 2.5s). |

## Services & metrics

- One local service per configured filter set, always state OK.
- Metric `count` — number of services matching the filter at agent runtime.

## Known limitations

- The site-local automation credential is restricted to a validated loopback URL. The default local HTTP connection does not cross a network boundary; explicit remote URLs retain TLS verification unless the operator deliberately opts out.
- The special agent uses the site-local automation secret, so it must run on (or as) the Checkmk site user.
- Filters are combined with `and`; there is no `or` between sub-conditions within a single entry.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `service_counter` version `2.1.4`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `service_counter/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `service_counter-1.0.0.mkp`, `service_counter-1.0.1.mkp`, `service_counter-2.0.0.mkp`, `service_counter-2.0.1.mkp`, `service_counter-2.1.1.mkp`, `service_counter-2.1.3.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Server-side calls:** `src/service_counter/server_side_calls/service_counter.py`.
- **Rulesets:** `src/service_counter/rulesets/service_counter.py`.
- **Executables:** `src/service_counter/libexec/agent_service_counter`.
- Registered special-agent names: `service_counter`.

### Validation

- Package-specific tests: `tests/test_service_counter_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- The source reads the local Checkmk automation secret. It must only transmit that credential to a validated loopback site URL.

### Troubleshooting

- Emitted Checkmk sections detected in source: `local`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
