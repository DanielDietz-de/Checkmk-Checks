# Spring Boot Actuator

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p9-blue)
<!-- compatibility-badges:end -->

Query a Spring Boot Actuator health endpoint and monitor every health component as its own service.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `spring_boot_actuator` version `1.0.1`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `spring_boot_actuator/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `spring_boot_actuator-1.0.0.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/spring_boot_actuator/agent_based/spring_boot_actuator.py`.
- **Server-side calls:** `src/spring_boot_actuator/server_side_calls/spring_boot_actuator.py`.
- **Rulesets:** `src/spring_boot_actuator/rulesets/spring_boot_actuator.py`.
- **Executables:** `src/spring_boot_actuator/libexec/agent_spring_boot_actuator`.
- **Check manuals:** `src/spring_boot_actuator/checkman/spring_boot_actuator`.
- Registered special-agent names: `spring_boot_actuator`.
- Registered check plug-in names: `spring_boot_actuator`.

### Validation

- Package-specific tests: `tests/test_spring_boot_actuator_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `spring_boot_actuator`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
## TLS trust and private CAs

TLS certificate verification remains enabled by default. To preserve Checkmk site isolation, the integration disables Requests proxy and `.netrc` inheritance with `trust_env = False` and passes certificate trust explicitly. The trust order is:

1. the rule's **Custom CA bundle** (`ca_file`);
2. `REQUESTS_CA_BUNDLE` from the Checkmk site environment;
3. `CURL_CA_BUNDLE` from the Checkmk site environment;
4. the operating system trust store.

The configured bundle must exist as a regular PEM file on the Checkmk server. An explicit certificate-verification opt-out, where supported, is mutually exclusive with a custom CA bundle and should be used only as a temporary compatibility measure. Environment CA variables are read deliberately even though proxy and `.netrc` inheritance remain disabled. For HTTP endpoints, CA bundle settings and CA environment variables are not evaluated because no TLS trust chain exists.

Troubleshooting order: verify the endpoint name matches the certificate, confirm the PEM path is readable by the site user, test the CA chain with the same site environment, and use the verification opt-out only to isolate a trust-chain problem. Removing `ca_file` falls back automatically to the site variables and then to the system trust store.
