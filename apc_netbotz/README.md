# APC Netbotz sensors

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p24-blue)
<!-- compatibility-badges:end -->

Additional SNMP checks for APC Netbotz environmental appliances, covering sensor types that are not monitored by the built-in Netbotz checks. Tested on APC Netbotz 750. Adds services for beacon, leak and vibration sensors.

## How it works

All three sections detect the device via `sysObjectID` starting with `.1.3.6.1.4.1.52674.500` and read three OIDs (sensor id, value, label) per sensor from the NetBotz50-MIB:

| Check | SNMP base | Sensor type |
| --- | --- | --- |
| `netbotz_beacon` | `.1.3.6.1.4.1.52674.500.4.2.14.1` | Beacon (`0` off = OK, `1` on = CRIT) |
| `netbotz_leak` | `.1.3.6.1.4.1.52674.500.4.2.13.1` | Leak (`0` noLeak = OK, `1` leakDetected = CRIT) |
| `netbotz_vibration` | `.1.3.6.1.4.1.52674.500.4.2.11.1` | Vibration (`0` noVibration = OK, `1` vibrationDetected = CRIT) |

Each sensor yields one service with the sensor id as item and the label shown in brackets in the summary.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/apc_netbotz/agent_based/beacon.py` | Beacon sensor section and check (service `Beacon <id>`). |
| `src/apc_netbotz/agent_based/leak.py` | Leak sensor section and check (service `Leak <id>`). |
| `src/apc_netbotz/agent_based/vibration.py` | Vibration sensor section and check (service `Vibration <id>`). |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the APC Netbotz device as an SNMP host and run service discovery.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `apc_netbotz` version `1.0.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `apc_netbotz/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `apc_netbotz-1.0.0.mkp`, `apc_netbotz-1.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/apc_netbotz/agent_based/beacon.py`, `src/apc_netbotz/agent_based/leak.py`, `src/apc_netbotz/agent_based/vibration.py`.
- Registered check plug-in names: `netbotz_beacon`, `netbotz_leak`, `netbotz_vibration`.

### Validation

- Package-specific tests: `tests/test_apc_netbotz_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
