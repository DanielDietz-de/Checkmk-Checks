# CSMON SAP Monitoring Connector

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p18-blue)
<!-- compatibility-badges:end -->

Connect CSMON SAP Monitoring Instances to your Checkmk using the CSMON RestAPI

Detailed Documentation can be found in the GIT Repo.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `csmon_connector` version `2.0.1`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `csmon/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `csmon_connector-1.0.0.mkp`, `csmon_connector-1.0.1.mkp`, `csmon_connector-2.0.0.mkp`, `csmon_connector-2.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Server-side calls:** `src/csmon/server_side_calls/agent.py`.
- **Rulesets:** `src/csmon/rulesets/agent.py`.
- **Executables:** `src/csmon/libexec/agent_csmon`.
- Registered special-agent names: `csmon`.

### Validation

- Package-specific tests: `tests/test_csmon_secret_command_arguments.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.

### Troubleshooting

- Emitted Checkmk sections detected in source: `check_mk`, `local`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
