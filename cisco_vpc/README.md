# Cisco VPC

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p18-blue)
<!-- compatibility-badges:end -->

Suite of SNMP-based checks for Cisco virtual Port Channel (vPC) redundancy pairs (Nexus). It creates three services per device covering the vPC role / dual-active detection, the peer-keepalive link status and the consistency of host-facing vPC links.

## How it works

All three sections detect Nexus hardware via a regex match on sysObjectID `.1.3.6.1.4.1.9.12.3.1.3.<4 digits>` and walk `CISCO-VPC-MIB` under `.1.3.6.1.4.1.9.9.807`:

- `cisco_vpc_role` (`.1.2.1.1`) — `cVpcRoleStatus` and `cVpcDualActiveDetectionStatus`. OK when no dual active is detected, optionally WARN if the role differs from the configured expectation.
- `cisco_vpc_status` (`.1.1.2.1`) — `cVpcPeerKeepAliveStatus`. OK only for status `alive` (2), CRIT otherwise.
- `cisco_vpc_host_link` (`.1.4.2.1`) — host-link consistency per ifIndex; OK when all entries report `success`, otherwise CRIT per bad interface. Names are resolved against the `if64` section.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cisco_vpc/agent_based/cisco_vpc_role.py` | vPC role and dual-active check. |
| `src/cisco_vpc/agent_based/cisco_vpc_status.py` | vPC peer keepalive check. |
| `src/cisco_vpc/agent_based/cisco_vpc_host_link.py` | vPC host-link consistency check (requires `if64`). |
| `src/cisco_vpc/rulesets/cisco_vpc_role.py` | Check parameter ruleset for the expected VPC role. |

## Installation

1. Install the MKP on the Checkmk site.
2. Run service discovery on a Nexus switch. Services `VPC Role`, `VPC Keepalive Status` and `VPC Host Link` appear where the MIB is populated.

## Configuration

Rule: **Parameters for discovered services -> Networking -> Cisco VPC Role**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `switch_role` | SingleChoice | Expected role: `primary_secondary`, `primary_primary`, `secondary_primary`, `secondary_secondary`, `no_peer_device`. WARN if the current role does not match. |

A migration function is included to map legacy integer values (`1`..`5`) to the new named choices.

## Services & metrics

- **Services:**
  - `VPC Role` — one per device
  - `VPC Keepalive Status` — one per device
  - `VPC Host Link` — one per device (requires `if64`)
- **State logic:** see "How it works" above.
- No metrics.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cisco_vpc` version `2.0.1`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cisco_vpc/src/info`; it declares 4 packaged files.
- Repository MKP artifacts present: `cisco_vpc-1.0.mkp`, `cisco_vpc-1.1.1.mkp`, `cisco_vpc-1.1.mkp`, `cisco_vpc-1.2.0.mkp`, `cisco_vpc-1.2.1.mkp`, `cisco_vpc-2.0.0.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/cisco_vpc/agent_based/cisco_vpc_host_link.py`, `src/cisco_vpc/agent_based/cisco_vpc_role.py`, `src/cisco_vpc/agent_based/cisco_vpc_status.py`.
- **Rulesets:** `src/cisco_vpc/rulesets/cisco_vpc_role.py`.
- Registered check plug-in names: `cisco_vpc_host_link`, `cisco_vpc_role`, `cisco_vpc_status`.

### Validation

- Package-specific tests: `tests/test_cisco_vpc_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
