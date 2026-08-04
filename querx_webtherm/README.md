# Querx Webtherm monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p35-blue)
<!-- compatibility-badges:end -->

SNMP monitoring for Querx Webtherm environmental sensors. Creates a
temperature and a humidity service per device using the built-in Checkmk
temperature and humidity check helpers, so standard WATO thresholds apply.

## How it works

Both sections are auto-detected with `contains(sysDescr, "Querx")` and
fetch from `.1.3.6.1.4.1.3444.1.14.1.2.1.5`:

| Section | OID | Parse | Service item |
| --- | --- | --- | --- |
| `querx_webtherm_temp` | `.1` | raw value / 10 (deg C) | `Temperature Sensor` |
| `querx_webtherm_humidity` | `.2` | raw value (percent) | `Humidity Sensor` |

The temperature check delegates to `cmk.plugins.lib.temperature.check_temperature`
(using a shared value store for trend calculations) and the humidity
check delegates to `cmk.plugins.lib.humidity.check_humidity`. Because they
use the standard check groups, any existing WATO rules for temperature /
humidity thresholds apply.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/querx_webtherm/agent_based/temp.py` | SNMP section and check plugin for the temperature sensor. |
| `src/querx_webtherm/agent_based/humidity.py` | SNMP section and check plugin for the humidity sensor. |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the Querx device as an SNMP host. Run service discovery to create
   the services `Temperature Sensor` and `Humidity Sensor`.

## Configuration

Because the checks reuse the built-in `temperature` and `humidity` check
groups, no dedicated WATO rules are shipped. Configure thresholds through
the standard Checkmk rules *Temperature* and *Humidity Levels*.

## Services & metrics

- `Temperature Sensor` - delegates to the standard Checkmk temperature
  check (metric `temp`).
- `Humidity Sensor` - delegates to the standard Checkmk humidity check
  (metric `humidity`).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `querx_webtherm` version `2.0.3`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `querx_webtherm/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `querx_webtherm-1.0.mkp`, `querx_webtherm-1.1.mkp`, `querx_webtherm-1.2.0.mkp`, `querx_webtherm-1.2.1.mkp`, `querx_webtherm-1.2.mkp`, `querx_webtherm-2.0.0.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/querx_webtherm/agent_based/humidity.py`, `src/querx_webtherm/agent_based/temp.py`.
- Registered check plug-in names: `querx_webtherm_humidity`, `querx_webtherm_temp`.

### Validation

- Package-specific tests: `tests/test_querx_webtherm_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
