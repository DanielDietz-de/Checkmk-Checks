# GUDE ATS Input Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p5-blue)
<!-- compatibility-badges:end -->

SNMP monitoring for GUDE Automatic Transfer Switch devices. One `Input Status` service per device reports which input feed (Primary or Secondary) is currently active and alerts when either feed goes missing or when the active feed has switched away from the one seen at discovery time.

## How it works

The section is fetched via SNMP from `.1.3.6.1.4.1.28507.41.1.5.11`:

- `.1.0` — Primary Power Available
- `.2.0` — Secondary Power Available
- `.4.0` — Current Channel (1 = Primary, 2 = Secondary)

Detection matches sysDescr containing `UTE ATS`. At discovery the active channel is frozen into the service parameters as `inital`. The check reports CRIT when the current channel differs from the stored initial channel, and also CRIT when either the Primary or Secondary input shows `0` (void / not redundant).

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cmk_addons_plugins/gude_ats/agent_based/ats.py` | SNMP section parser and check plugin. |

## Installation

1. Install the MKP on the Checkmk site.
2. Configure SNMP access to the GUDE ATS device.
3. Run service discovery — a single `Input Status` service is created.

## Services & metrics

- **Service:** `Input Status`
- **State logic:** CRIT if the active channel differs from the one seen at discovery, or if any input is reported as void.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `gude_ats` version `2.0.3`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `gude_ats/src/info`; it declares 1 packaged files.
- Repository MKP artifacts present: `gude_ats-1.0.1.mkp`, `gude_ats-1.0.mkp`, `gude_ats-2.0.0.mkp`, `gude_ats-2.0.1.mkp`, `gude_ats-2.0.2.mkp`, `gude_ats-2.0.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/gude_ats/agent_based/ats.py`.
- Registered check plug-in names: `gude_ats`.

### Validation

- Package-specific tests: `tests/test_gude_ats_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
