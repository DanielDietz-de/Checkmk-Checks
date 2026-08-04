# Cisco Portsecurity Status

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p18-blue)
<!-- compatibility-badges:end -->

Reports on Cisco switches whether any administratively up port has Port Security disabled. A single service `Port Security Status` is created per device; it goes WARN when at least one non-excluded port has port security turned off.

## How it works

The SNMP section `cisco_portsec` joins two SNMP trees:

- `.1.3.6.1.2.1.2.2.1` / `.1.3.6.1.2.1.31.1.1.1.18` — port name, ifAdminStatus, alias
- `.1.3.6.1.4.1.9.9.315.1.2.1.1` (`CISCO-PORT-SECURITY-MIB::cpsIfConfigTable`) — `cpsIfPortSecurityEnable` (1=yes, 2=no), operational status, violation count, last MAC

Detection requires a sysDescr containing `cisco` and that the port security table exists. Administratively down ports (`ifAdminStatus == 2`) and any interface whose name or alias matches the exception list are skipped.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cisco_portsec/agent_based/cisco_portsec.py` | SNMP section and check plugin. |
| `src/cisco_portsec/rulesets/agent.py` | Check parameters ruleset (exception list). |

## Installation

1. Install the MKP on the Checkmk site.
2. Run service discovery on a Cisco switch host. The service `Port Security Status` appears on devices where the port security table has entries.

## Configuration

Rule: **Parameters for discovered services -> Networking -> Cisco Portsecurity Status**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `exceptions` | List of strings | Interface names or alias prefixes that must not be checked. Alias matching uses `startswith`. |

## Services & metrics

- **Service:** `Port Security Status` — one per host.
- **State logic:** WARN if any port that is up and not excluded has port security disabled, UNKNOWN if the enable state cannot be parsed, otherwise OK.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cisco_portsec` version `1.0.4`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cisco_portsec/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `cisco_portsec-1.0.0.mkp`, `cisco_portsec-1.0.1.mkp`, `cisco_portsec-1.0.3.mkp`, `cisco_portsec-1.0.4.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/cisco_portsec/agent_based/cisco_portsec.py`.
- **Rulesets:** `src/cisco_portsec/rulesets/agent.py`.
- Registered check plug-in names: `cisco_portsec`.

### Validation

- Package-specific tests: `tests/test_cisco_portsec_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
