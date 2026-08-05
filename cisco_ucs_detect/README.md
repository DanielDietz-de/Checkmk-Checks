# Cisco UCS: detect standalone CIMC / C-series servers

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p19-blue)
<!-- compatibility-badges:end -->

Broadens the discovery of the built-in cisco_ucs_* checks.
Upstream detection (cmk.plugins.lib.cisco_ucs.DETECT) only matches a
fixed whitelist of sysObjectIDs, so standalone Cisco IMC (CIMC)
appliance servers and newer UCS C-series -- e.g. SNS-8355-K9 /
UCS C225 M8 -- discover no services even though they fully serve the
CISCO-UNIFIED-COMPUTING-MIB (.1.3.6.1.4.1.9.9.719).

This package shadows cmk.plugins.lib.cisco_ucs, loads the genuine
upstream module dynamically, re-exports it unchanged, and only
broadens DETECT to additionally match any device exposing the UCS
compute rack-unit table (.1.3.6.1.4.1.9.9.719.1.9.35.1.43). This
affects all cisco_ucs_* checks (system, cpu, mem, fan, psu, hdd,
raid, lun, temp_cpu, temp_env, faults).

Note: a stored SNMP walk must contain the MIB-2 system OIDs
(.1.3.6.1.2.1.1.1.0 / .2.0); a walk restricted to the .9.9.719
subtree makes the Checkmk SNMP scan abort before detection runs.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cisco_ucs_detect` version `1.0.0`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cisco_ucs_detect/src/info`; it declares 1 packaged files.
- Repository MKP artifacts present: `cisco_ucs_detect-1.0.0.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Other packaged source:** `src/cmk/plugins/lib/cisco_ucs.py`.
- No special-agent or agent-based check registration was detected; use the component paths above to identify the package entry point.

### Validation

- Package-specific tests: `tests/test_cisco_ucs_detect_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
