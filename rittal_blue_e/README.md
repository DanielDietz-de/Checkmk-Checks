# Rittal Blue e+ Cooling Unit Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p25-blue)
<!-- compatibility-badges:end -->

Monitors **Rittal Blue e+** cooling units that are connected to a Rittal
**CMC III Processing Unit** or **IoT Interface** and polled via SNMP
(enterprise OID `.1.3.6.1.4.1.2606.7`).

## Why a separate plugin

The cmciii check bundled with Checkmk classifies sensors with a fixed
`sensor_type()` table that does not recognise the Blue e+ variable naming
scheme (`Internal Temperature`, `Monitoring.Cooling.Status`,
`Monitoring.Compressor.Speed`, …). As a result Blue e+ units are **never
discovered** by the built-in check, even though all of their data is present
in the CMC III variable table.

This plugin reads the same variable table (`.1.3.6.1.4.1.2606.7.4.2.2.1`),
filters to sub-devices whose device-table type is `Blue e+`
(`.1.3.6.1.4.1.2606.7.4.1.2.1`) and creates dedicated services.

## Services

Service names follow the Checkmk style. With more than one Blue e+ unit on
the same CMC III, the device name is appended in parentheses to keep the
items unique.

| Service | Content |
|---|---|
| `Cooling Unit <name>` | Aggregated health of all component status fields (Cooling, Air Circuits, Fans, Compressor, EEV, Filter, Door, Electronics, Condensate, System Messages, Error List, temperature alarms). Performance data: input power, cooling capacity, EER. |
| `Temperature Internal` / `Temperature Ambient` / `Temperature External` | Temperature with the appliance thresholds (overridable) and perfdata. |
| `Fan Internal` / `Fan External` / `Compressor` | Internal fan, external fan and compressor speed in percent with component status. |

Sensors/components reporting status *not available* are not discovered.

## Status mapping

The IoT Interface firmware reports only the numeric status code
(`cmcIIIVarValueStr` is empty), so codes are mapped from the
`RITTAL-CMC-III-MIB` `cmcIIIMsgStatus` enumeration to text and to a Checkmk
state. Defaults: `OK`/`closed`/`standby`/`active`/`detected` → OK,
`warning`/`high warning`/`low warning`/`config changed` → WARN,
`error`/`alarm`/`high alarm`/`low alarm`/`no power`/`lost` → CRIT. Override
per service with the **Rittal Blue e+ unit health** ruleset.

## Rulesets

- **Rittal Blue e+ unit health** — override the state per status text.
- **Rittal Blue e+ temperature** — upper temperature levels (otherwise the
  appliance thresholds are used).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `rittal_blue_e` version `1.1.1`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `rittal_blue_e/src/info`; it declares 5 packaged files.
- Repository MKP artifacts present: `rittal_blue_e-1.0.0.mkp`, `rittal_blue_e-1.1.0.mkp`, `rittal_blue_e-1.1.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/rittal_blue_e/agent_based/rittal_blue_e.py`.
- **Rulesets:** `src/rittal_blue_e/rulesets/rittal_blue_e.py`.
- **Check manuals:** `src/rittal_blue_e/checkman/rittal_blue_e`, `src/rittal_blue_e/checkman/rittal_blue_e_fan`, `src/rittal_blue_e/checkman/rittal_blue_e_temp`.
- Registered check plug-in names: `rittal_blue_e`, `rittal_blue_e_fan`, `rittal_blue_e_temp`.

### Validation

- Package-specific tests: `tests/test_rittal_blue_e_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
