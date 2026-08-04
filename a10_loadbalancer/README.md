# A10 Loadbalancer Checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

SNMP-based monitoring for A10 AX loadbalancer appliances. Adds services for fans, power supplies and system temperature on top of the generic SNMP discovery.

## How it works

All three checks detect A10 devices via `sysObjectID` `.1.3.6.1.4.1.22610.1.3.22` and read from the A10-AX-MIB under `.1.3.6.1.4.1.22610.2.4.1.5`:

- Fans: `axFanName/Status/Speed` at `.9.1.{2,3,4}` — states `4..7` are OK, anything else CRIT.
- Power supplies: `axPowerSupplyName/Status` at `.12.1.{2,3}` — `on` is OK, `absent` CRIT, `off`/`unknown` WARN. Only supplies currently reporting `on` are discovered.
- Temperature: `axSyshwPhySystemTemp` at `.1` — delegates to the built-in `check_temperature` helper, so WARN/CRIT can be configured via the temperature ruleset.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/checks/a10_loadbalancer_fan` | Fan SNMP check (legacy `check_info` API). |
| `src/checks/a10_loadbalancer_power` | Power supply SNMP check. |
| `src/checks/a10_loadbalancer_temp` | System temperature check using `check_temperature`. |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the A10 device as an SNMP host and run service discovery. The three checks auto-detect via `sysObjectID`.

## Services & metrics

- `Fan <name>` — one per fan, reports state and RPM.
- `Power Supply <name>` — one per power supply reporting `on` at discovery time.
- `Temperature System` — one service, WARN/CRIT from the temperature ruleset.

## Known limitations

- Uses the pre-2.0 `check_info` API. Still loads on newer Checkmk versions as long as the legacy API is available; needs porting to `cmk.agent_based.v2` if it ever drops.
- Power supplies that are in state `absent` or `off` at discovery time are not created as services.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `a10_loadbalancer` version `2.0.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `a10_loadbalancer/src/info`; it declares 6 packaged files.
- Repository MKP artifacts present: `a10_loadbalancer-1.0.1.mkp`, `a10_loadbalancer-1.0.2.mkp`, `a10_loadbalancer-1.0.mkp`, `a10_loadbalancer-2.0.0.mkp`, `a10_loadbalancer-2.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/a10_loadbalancer/agent_based/a10_loadbalancer_fan.py`, `src/a10_loadbalancer/agent_based/a10_loadbalancer_power.py`, `src/a10_loadbalancer/agent_based/a10_loadbalancer_temp.py`.
- **Check manuals:** `src/a10_loadbalancer/checkman/a10_loadbalancer_fan`, `src/a10_loadbalancer/checkman/a10_loadbalancer_power`, `src/a10_loadbalancer/checkman/a10_loadbalancer_temp`.
- Registered check plug-in names: `a10_loadbalancer_fan`, `a10_loadbalancer_power`, `a10_loadbalancer_temp`.

### Validation

- Package-specific tests: `tests/test_a10_loadbalancer_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
