# Veritas Flex Appliance

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p25-blue)
<!-- compatibility-badges:end -->

Special agent for Veritas Flex storage appliances. Logs in against the Flex REST API, reads node hardware and services health, and enumerates instances; the results are emitted as a `<<<local>>>` section, so each check is a Checkmk local check.

## How it works

1. POST to `https://<host>/api/v1/login` with username/password, token with TTL 30, stored as `X-Auth-Token`.
2. GET `v1/nodes` to enumerate cluster nodes.
3. For every node: GET `v1/nodes/<node>/health/hardware` and `v1/nodes/<node>/health/services`. A two-key response body is treated as healthy (state 0); anything else is degraded (state 2).
4. GET `v3/instances` and emit one local check per instance — OK when `status == ONLINE`, CRIT otherwise.
5. All output is printed below a single `<<<local>>>` section header in the legacy local-check line format.

```text
<<<local>>>
0 "node01 Hardware Health" - Hardware is healthy
0 "node01 Services Health" - Services are healthy
0 instance01 - is ONLINE
```

## Package contents

| Path | Purpose |
| --- | --- |
| `src/veritas_flex/libexec/agent_veritas` | Special agent (Python, uses `requests`). |
| `src/veritas_flex/rulesets/agent.py` | WATO `SpecialAgent` rule *Veritas Flex Appliance* (topic *Storage*). |
| `src/veritas_flex/server_side_calls/veritas.py` | Builds the command: `<api_url> -u <user> -p <password>`. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create an API user on the Flex appliance.
3. Add the appliance as a host in Checkmk and create a *Veritas Flex Appliance* special agent rule for it.
4. Discovery creates one service per hardware/services health report and one per instance, all driven by the standard local check plugin.

## Configuration

WATO rule: *Setup > Agents > Other integrations > Veritas Flex Appliance*.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `api_url` | String (required) | Hostname or host:port used in `https://<api_url>/api/`. |
| `username` | String (required) | Flex API user. |
| `password` | Password (required) | Flex API password. |

## Known limitations

- Health evaluation is naive: the code only counts top-level JSON keys in the response (`len(json_body.keys())`) to decide healthy vs degraded, with no inspection of actual fault details.
- The agent logs into `/tmp/checkMK_flex.log` on the Checkmk site and does not call `do_logout()`.
- All results flow through `<<<local>>>`, so there is no dedicated check plugin, ruleset or metric — configuration must happen via the standard *Local checks* rules.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `veritas_flex` version `1.0.3`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `veritas_flex/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `veritas_flex-1.0.2.mkp`, `veritas_flex-1.0.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Server-side calls:** `src/veritas_flex/server_side_calls/veritas.py`.
- **Rulesets:** `src/veritas_flex/rulesets/agent.py`.
- **Executables:** `src/veritas_flex/libexec/agent_veritas`.
- Registered special-agent names: `veritas`.

### Validation

- Package-specific tests: `tests/test_veritas_flex_secret_command_arguments.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `local`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
## TLS trust and private CAs

TLS certificate verification remains enabled by default. To preserve Checkmk site isolation, the integration disables Requests proxy and `.netrc` inheritance with `trust_env = False` and passes certificate trust explicitly. The trust order is:

1. the rule's **Custom CA bundle** (`ca_file`);
2. `REQUESTS_CA_BUNDLE` from the Checkmk site environment;
3. `CURL_CA_BUNDLE` from the Checkmk site environment;
4. the operating system trust store.

The configured bundle must exist as a regular PEM file on the Checkmk server. An explicit certificate-verification opt-out, where supported, is mutually exclusive with a custom CA bundle and should be used only as a temporary compatibility measure. Environment CA variables are read deliberately even though proxy and `.netrc` inheritance remain disabled.

Troubleshooting order: verify the endpoint name matches the certificate, confirm the PEM path is readable by the site user, test the CA chain with the same site environment, and use the verification opt-out only to isolate a trust-chain problem. Removing `ca_file` falls back automatically to the site variables and then to the system trust store.
