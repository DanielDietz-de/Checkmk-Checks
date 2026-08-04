# Arista Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

SNMP-based checks for Arista Networks devices using the generic entity sensor MIB. Adds services for temperature, fans and voltage derived from `entPhysicalDescr` combined with `entPhySensorValue/OperStatus/Units`.

## How it works

Detection is via `sysDescr` starting with `Arista Networks`. The parser joins four tables:

- `.1.3.6.1.2.1.47.1.1.1.1.2` — entity descriptions
- `.1.3.6.1.2.1.99.1.1.1.4` — sensor values
- `.1.3.6.1.2.1.99.1.1.1.5` — sensor status (`1` = OK, `2` = warning)
- `.1.3.6.1.2.1.99.1.1.1.6` — sensor units (`Celsius`, `RPM`, `Volts`, ...)

Items are discovered by unit:

- `arista` — unit `Celsius`, excluding descriptions starting with `PhyAlaska`. Values are divided by 10 and handed to `check_temperature`. Service `Temperature <name>`.
- `arista.fan` — unit `RPM`. Service `Fan <name>`, default lower levels 2000 / 1000 RPM, upper 9000 / 9500 RPM, using `check_fan`. The `Fan` prefix is stripped from the item name.
- `arista.voltage` — unit `Volts`. Service `Voltage <name>`, default lower levels 50 / 50 V.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/checks/arista` | Combined section + temperature, fan and voltage checks (legacy `check_info` API). |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the Arista device as an SNMP host and run service discovery.

## Services & metrics

- `Temperature <name>` — WARN/CRIT from the temperature ruleset, with sensor status folded in.
- `Fan <name>` — RPM via `check_fan` with the lower/upper defaults shown above.
- `Voltage <name>` — voltage in volts with lower WARN/CRIT levels.

## Known limitations

- Uses the pre-2.0 `check_info` API with `temperature.include` and `fan.include`. Will keep working as long as Checkmk still ships the legacy API and include files.
- Entity descriptions starting with `PhyAlaska` are skipped for the temperature discovery to avoid spurious sensors.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `arista` version `2.0.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `arista/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `arista-1.0.0.mkp`, `arista-1.0.1.mkp`, `arista-1.0.2.mkp`, `arista-1.0.4.mkp`, `arista-2.0.0.mkp`, `arista-2.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/arista/agent_based/arista.py`.
- **Rulesets:** `src/arista/rulesets/arista_voltage.py`.
- **Check manuals:** `src/arista/checkman/arista`, `src/arista/checkman/arista_fan`, `src/arista/checkman/arista_voltage`.
- Registered check plug-in names: `arista`, `arista_fan`, `arista_voltage`.

### Validation

- Package-specific tests: `tests/test_arista_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
