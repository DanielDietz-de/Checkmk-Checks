# Cisco stack extras

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p4-blue)
<!-- compatibility-badges:end -->

Consolidated add-on checks for Cisco StackWise / Catalyst stacks. Everything
here covers scenarios that the Checkmk core does **not** ship a plugin for.
Checks previously covered by the standalone packages
`catalyst_switch_state`, `cisco_distr_stack_port` and the now obsolete
`cisco_ip_sla` custom plugin are covered here, except for `cisco_ip_sla`
which Checkmk 2.4 ships natively — install no custom package for that one.

> **Not included / removed:** `cisco_redundancy` and `cisco_stackwise` were
> removed from this MKP because Checkmk 2.4 ships `cisco_redundancy` and
> `cisco_stack` with equivalent functionality. If you had services from the
> old `cisco 2.0.0` package, rediscover after migrating to 2.4 — the
> built-in checks take over automatically.

## Provided check plugins

| Check plugin | Service | Purpose |
| --- | --- | --- |
| `cisco_stackring` | `Stackring` | CRIT when a StackWise ring is not redundant (>= 2 members). |
| `catalyst_switch_state` | `State Switch <n>` | Per-switch role + state for Catalyst 9500X-class stacks (sysObjectID `.1.3.6.1.4.1.9.1.2871`) that the built-in `cisco_stack` does not detect. |
| `cisco_distr_stack_port` | `Distributed stack port status <port>` | Operational status of distributed stack ports including the neighbor side. |

## Rulesets

| Ruleset | Applies to | Purpose |
| --- | --- | --- |
| `Catalyst Switch State` (Networking) | `catalyst_switch_state` | Pin the expected switch role (`master`, `member`, `not_member`, `standby`). |

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cisco/agent_based/stackring.py` | `cisco_stackring` section + check. |
| `src/cisco/agent_based/catalyst_switch_state.py` | `catalyst_switch_state` section + check. |
| `src/cisco/agent_based/distr_stack_port.py` | `cisco_distr_stack_port` section + check. |
| `src/cisco/rulesets/catalyst_switch_state.py` | WATO ruleset for the expected switch role. |
| `src/checkman/cisco_stackring` | Check manpage. |

## Installation

1. If a previous `cisco_ip_sla` / `catalyst_switch_state` /
   `cisco_distr_stack_port` MKP is installed, uninstall it.
2. Install this MKP on the Checkmk site (>= 2.4).
3. Run service discovery on the Cisco SNMP hosts.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `cisco` version `2.2.1`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `cisco/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `cisco-2.1.0.mkp`, `cisco-2.2.0.mkp`, `cisco-2.2.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/cisco/agent_based/catalyst_switch_state.py`, `src/cisco/agent_based/distr_stack_port.py`, `src/cisco/agent_based/stackring.py`.
- **Rulesets:** `src/cisco/rulesets/catalyst_switch_state.py`.
- **Check manuals:** `src/cisco/checkman/cisco_stackring`.
- Registered check plug-in names: `catalyst_switch_state`, `cisco_distr_stack_port`, `cisco_stackring`.

### Validation

- Package-specific tests: `tests/test_cisco_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
