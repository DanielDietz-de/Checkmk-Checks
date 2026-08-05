# Semu Frame Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0p1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0-blue)
<!-- compatibility-badges:end -->

Special agent that queries a SEMU single-sensor device over its HTTPS API and produces a single `Framerate` service which reports the measured frames per second plus the illumination status.

## How it works

1. The special agent calls `https://<host>/api/v5/singlesensor/status` using HTTP Basic authentication (TLS certificate verification is disabled).
2. It prints the JSON response as key/value pairs under the `<<<semu_frames>>>` section.
3. The `semu_frames` check parses the section, computes a rate on `frames_processed` via `get_rate()` and evaluates lower levels on that rate. It also reports the current `illumination` value.

### Example agent output

```text
<<<semu_frames>>>
mac_address D8:80:39:D3:DE:77
frames_processed 8354128
illumination SUFFICIENT
measured_sensor_direction [0.00884352, -0.00114911, -0.99996]
measured_alpha_deg -0.0658392
measured_beta_deg -0.506703
```

## Package contents

| Path | Purpose |
| --- | --- |
| `src/semu/libexec/agent_semu` | Special agent (`host`, `user`, `password` as positional args). |
| `src/semu/server_side_calls/agent_semu.py` | Server-side call wiring. |
| `src/semu/rulesets/ruleset.py` | WATO rules for the special agent and the framerate check. |
| `src/semu/agent_based/frames.py` | Section parser and `semu_frames` check plugin. |

## Installation

1. Install the MKP on the Checkmk site.
2. Create a Checkmk host for the SEMU device.
3. Configure the *SEMU Framerate* special agent rule with credentials.
4. Run service discovery.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> SEMU Framerate**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `username` | String | HTTP Basic user. |
| `password` | Password | HTTP Basic password. |

Rule: **Parameters for discovered services -> Semu Framerate**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `levels` | Lower levels (frames/s) | WARN/CRIT when the rate drops below the given thresholds. Default `(10, 5)`. |

## Services & metrics

- **Service:** `Framerate`
- **Metric:** `frames` (frames per second, derived from `frames_processed` via rate calculation)
- Illumination value is reported as OK result text.

## Known limitations

- TLS verification is enabled by default. A deliberate `--no-cert-check` compatibility option exists for isolated legacy appliances; prefer a trusted certificate or CA bundle.
- Only a single sensor endpoint is queried; multi-sensor SEMU devices would need an extension.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `semu` version `1.0.3`; minimum Checkmk version `2.3.0p1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `semu/src/info`; it declares 4 packaged files.
- Repository MKP artifacts present: `semu-0.0.1.mkp`, `semu-1.0.0.mkp`, `semu-1.0.1.mkp`, `semu-1.0.2.mkp`, `semu-1.0.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/semu/agent_based/frames.py`.
- **Server-side calls:** `src/semu/server_side_calls/agent_semu.py`.
- **Rulesets:** `src/semu/rulesets/ruleset.py`.
- **Executables:** `src/semu/libexec/agent_semu`.
- Registered special-agent names: `semu`.
- Registered check plug-in names: `semu_frames`.

### Validation

- Package-specific tests: `tests/test_semu_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `semu_frames`.
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
