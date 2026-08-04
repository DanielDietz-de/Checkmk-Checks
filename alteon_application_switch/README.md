# Alteon Application Switch monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p7-blue)
<!-- compatibility-badges:end -->

SNMP-based monitoring for Radware Alteon Application Switch appliances. Provides checks for MP/SP CPU cores, memory, interfaces, throughput, session counters, virtual and real server statistics and VRRP state.

## How it works

All sections detect Alteon devices via `sysDescr` starting with `Alteon Application Switch` and query the private MIB under `.1.3.6.1.4.1.1872.2.5`:

- `alteon_cpu` — MP and SP CPU utilization over 1s / 4s / 64s. One service per core, with a shared upper-levels ruleset.
- `alteon_memory` — global MP memory stats (total, free, virtual, RSS) and per-SP-core memory usage, peak usage and front-end session counters.
- `alteon_interface` — physical interfaces with rates derived via `get_rate`.
- `alteon_throughput` — maximum, peak and current throughput in bits per second.
- `alteon_sessions`, `alteon_sessions_slb`, `alteon_sessions_ssl` — session counters per SP core (current, 4s, 64s, max).
- `alteon_rserver` — real server counters (current / peak sessions, new sessions per second, failures, bytes per second).
- `alteon_vserver` — virtual server counters (current / peak sessions, new sessions per second, HTTP header sessions, bytes per second) keyed by label.
- `alteon_vrrp_status` — VRRP router state per virtual IP (`init`, `master`, `backup`, ...).

## Package contents

| Path | Purpose |
| --- | --- |
| `src/alteon_application_switch/agent_based/alteon_cpu.py` | MP/SP CPU section and check. |
| `src/alteon_application_switch/agent_based/alteon_memory.py` | Global and per-core memory. |
| `src/alteon_application_switch/agent_based/alteon_interface.py` | Interface counters. |
| `src/alteon_application_switch/agent_based/alteon_throughput.py` | Throughput (max / peak / current). |
| `src/alteon_application_switch/agent_based/alteon_sessions.py` | Sessions per SP core. |
| `src/alteon_application_switch/agent_based/alteon_sessions_slb.py` | SLB session counters. |
| `src/alteon_application_switch/agent_based/alteon_sessions_ssl.py` | SSL session counters. |
| `src/alteon_application_switch/agent_based/alteon_rserver.py` | Real server statistics. |
| `src/alteon_application_switch/agent_based/alteon_vserver.py` | Virtual server statistics. |
| `src/alteon_application_switch/agent_based/alteon_vrrp_status.py` | VRRP router state. |
| `src/alteon_application_switch/rulesets/*.py` | WATO rules for CPU, memory, sessions, throughput and VRRP. |
| `src/alteon_application_switch/checkman/*` | Check manual pages. |
| `src/alteon_application_switch/graphing/metrics.py` | Metric definitions. |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the Alteon device as an SNMP host and run service discovery.

## Configuration

Available WATO rulesets:

| Ruleset | Purpose |
| --- | --- |
| `alteon_cpu` | Upper levels for CPU utilization per core (default 80 / 90 %). |
| `alteon_memory` | Levels for memory usage. |
| `alteon_sessions` | Levels for session counters. |
| `alteon_throughput` | Levels for current throughput. |
| `alteon_vrrp_status` | Expected VRRP state mapping. |

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `alteon_application_switch` version `3.0.0-dev3`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `alteon_application_switch/src/info`; it declares 25 packaged files.
- Repository MKP artifacts present: `alteon_application_switch-2.1.8.mkp`, `alteon_application_switch-2.1.9.mkp`, `alteon_application_switch-3.0.0-dev1.mkp`, `alteon_application_switch-3.0.0-dev2.mkp`, `alteon_application_switch-3.0.0-dev3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/alteon_application_switch/agent_based/alteon_cpu.py`, `src/alteon_application_switch/agent_based/alteon_interface.py`, `src/alteon_application_switch/agent_based/alteon_memory.py`, `src/alteon_application_switch/agent_based/alteon_rserver.py`, `src/alteon_application_switch/agent_based/alteon_sessions.py`, `src/alteon_application_switch/agent_based/alteon_sessions_slb.py`, `src/alteon_application_switch/agent_based/alteon_sessions_ssl.py`, `src/alteon_application_switch/agent_based/alteon_throughput.py` and 2 more.
- **Rulesets:** `src/alteon_application_switch/rulesets/alteon_cpu.py`, `src/alteon_application_switch/rulesets/alteon_memory.py`, `src/alteon_application_switch/rulesets/alteon_sessions.py`, `src/alteon_application_switch/rulesets/alteon_throughput.py`, `src/alteon_application_switch/rulesets/alteon_vrrp_status.py`.
- **Graphing:** `src/alteon_application_switch/graphing/metrics.py`.
- **Check manuals:** `src/alteon_application_switch/checkman/alteon_cpu`, `src/alteon_application_switch/checkman/alteon_memory`, `src/alteon_application_switch/checkman/alteon_rserver`, `src/alteon_application_switch/checkman/alteon_sessions`, `src/alteon_application_switch/checkman/alteon_sessions_slb`, `src/alteon_application_switch/checkman/alteon_sessions_ssl`, `src/alteon_application_switch/checkman/alteon_throughput`, `src/alteon_application_switch/checkman/alteon_vrrp_status` and 1 more.
- Registered check plug-in names: `alteon_cpu`, `alteon_interface`, `alteon_memory`, `alteon_rserver`, `alteon_sessions`, `alteon_sessions_slb`, `alteon_sessions_ssl`, `alteon_throughput`, `alteon_vrrp_status`, `alteon_vserver`.

### Validation

- Package-specific tests: `tests/test_alteon_application_switch_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
