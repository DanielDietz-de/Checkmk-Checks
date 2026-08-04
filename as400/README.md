# AS400 Checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p35-blue)
<!-- compatibility-badges:end -->

SNMP checks for IBM AS/400 (OS/400) systems. Monitors CPU load, active jobs, logged-in users and the current number of TCP connections. Based on the earlier `check_mk-as400_checks` project but rewritten for the modern `cmk.agent_based.v2` API.

## How it works

All four sections detect the host via `sysDescr` starting with `IBM OS/400` and each query a single scalar OID:

| Check | OID | What it reads |
| --- | --- | --- |
| `as400_cpu` | `.1.3.6.1.4.1.2.6.4.5.1.0` | CPU utilization in tenths of percent. Divided by 100 and handed to `check_cpu_load` as 15-minute load. |
| `as400_jobs` | `.1.3.6.1.2.1.25.1.6.0` | Number of running jobs. |
| `as400_users` | `.1.3.6.1.2.1.25.1.5.0` | Number of logged-in users. |
| `as400_tcp_connections` | `.1.3.6.1.2.1.6.9.0` | Current number of TCP connections. |

## Package contents

| Path | Purpose |
| --- | --- |
| `src/as400/agent_based/cpu.py` | CPU load section and check. |
| `src/as400/agent_based/jobs.py` | Jobs section and check. |
| `src/as400/agent_based/users.py` | Logged-in users section and check. |
| `src/as400/agent_based/connections.py` | TCP connections section and check. |
| `src/as400/agent_based/lib.py` | Shared `DETECT_AS400` and `parse_as400` helpers. |
| `src/as400/rulesets/cpu.py` | WATO rule `as400_cpu`. |
| `src/as400/rulesets/jobs.py` | WATO rule `as400_jobs`. |
| `src/as400/rulesets/users.py` | WATO rule `as400_users`. |
| `src/as400/rulesets/connections.py` | WATO rule `as400_tcp_connections`. |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the AS/400 system as an SNMP host and run service discovery.

## Configuration

Each check has its own ruleset with upper levels:

| Service | Ruleset | Default levels |
| --- | --- | --- |
| `CPU load` | `as400_cpu` | 80 / 90 (as 15-minute load via `check_cpu_load`) |
| `Jobs` | `as400_jobs` | 9000 / 9500 |
| `Users` | `as400_users` | 9000 / 9500 |
| `Connections` | `as400_tcp_connections` | 900000 / 950000 |

## Services & metrics

- `CPU load` — uses the built-in `check_cpu_load` helper; only the 15-minute slot is driven from the SNMP value.
- `Jobs` — metric `jobs`.
- `Users` — metric `users`.
- `Connections` — metric `tcp_connections`.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `as400` version `3.0.3`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `as400/src/info`; it declares 9 packaged files.
- Repository MKP artifacts present: `AS400-2.0.mkp`, `AS400-2.1.mkp`, `as400-2.1.1.mkp`, `as400-2.1.2.mkp`, `as400-3.0.0.mkp`, `as400-3.0.1.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/as400/agent_based/connections.py`, `src/as400/agent_based/cpu.py`, `src/as400/agent_based/jobs.py`, `src/as400/agent_based/lib.py`, `src/as400/agent_based/users.py`.
- **Rulesets:** `src/as400/rulesets/connections.py`, `src/as400/rulesets/cpu.py`, `src/as400/rulesets/jobs.py`, `src/as400/rulesets/users.py`.
- Registered check plug-in names: `as400_cpu`, `as400_jobs`, `as400_tcp_connections`, `as400_users`.

### Validation

- Package-specific tests: `tests/test_as400_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
