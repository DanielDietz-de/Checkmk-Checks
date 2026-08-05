# ADFS Certificate Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p19-blue)
<!-- compatibility-badges:end -->

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `adfs_certificates` version `1.0.1`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `adfs_certificates/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `adfs_certificates-1.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/adfs_certificates/agent_based/certificates.py`.
- **Server-side calls:** `src/adfs_certificates/server_side_calls/agent.py`.
- **Rulesets:** `src/adfs_certificates/rulesets/agent.py`.
- **Executables:** `src/adfs_certificates/libexec/agent_adfs_certificates`.
- **Check manuals:** `src/adfs_certificates/checkman/adfs_certificates`.
- Registered special-agent names: `adfs_certificates`.
- Registered check plug-in names: `adfs_certificates`.

### Validation

- Package-specific tests: `tests/test_adfs_certificates_integrity.py`, `tests/test_adfs_certificates_transport.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- The source performs network or remote-system access. Keep timeouts bounded, validate responses, and prevent authenticated redirects or unintended environment-proxy use.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `adfs_certificates`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
