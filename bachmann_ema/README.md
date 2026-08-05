# Bachmann EMA Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0p1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p25-blue)
<!-- compatibility-badges:end -->

SNMP check for Bachmann BlueNet EMA (Environmental Monitoring Adapter) GPIO ports. Discovers one service per enabled GPIO sensor and reports its mode, switch state and entity status.

## How it works

The plugin [`bachmann_ema.py`](src/bachmann_ema/agent_based/bachmann_ema.py) registers an SNMP section `bluenet_ema` that triggers on devices whose `sysDescr` starts with `Linux` and whose `sysLocation` starts with `Bachmann`. It walks `.1.3.6.1.4.1.31770.2.2.5.3.1` (BlueNet2 GPIO MIB) and collects, per GPIO pair:

- `5.1.4` / `5.1.5` — GPIO input IDs
- `8.1.4` / `8.1.5` — GPIO mode (`BlueNet2GPIOMode`)
- `10.1.4` / `10.1.5` — GPIO state
- `9.1.4` / `9.1.5` — GPIO switch

Services are discovered only where the mode is `enabled` (2) or `s0` (6). The check maps raw integer modes to human readable strings (`disabled`, `enabled`, `s0`, `undefined`), likewise for switch state (`on`, `off`, `switchable`, ...) and entity state (`ok`, `alarm`, `warning`, `armed`, `disarmed`, ...). An entity state of `39` (`armed`) is reported as CRIT; all other states are reported as OK.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/bachmann_ema/agent_based/bachmann_ema.py` | SNMP section parser, discovery and check. |

## Installation

1. Install the MKP on the Checkmk site.
2. Configure SNMP access (community or v3) for the EMA device and run service discovery. Services are named `EMA <input>/1` or `EMA <input>/2`.

## Services & metrics

- **Service:** `EMA %s` (GPIO pair)
- **State logic:** CRIT when the entity state is `armed` (39); otherwise OK.
- **Metrics:** none.

## Known limitations

- Only GPIOs whose mode is `enabled` or `s0` are discovered; disabled inputs are skipped silently.
- State mapping is hardcoded; only `armed` triggers CRIT, even though the MIB also exposes `alarm`, `errorHigh`, `lost`, `updateError` etc. These currently all surface as OK.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `bachmann_ema` version `1.1.2`; minimum Checkmk version `2.3.0p1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `bachmann_ema/src/info`; it declares 1 packaged files.
- Repository MKP artifacts present: `bachmann_ema-1.1.0.mkp`, `bachmann_ema-1.1.1.mkp`, `bachmann_ema-1.1.2.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/bachmann_ema/agent_based/bachmann_ema.py`.
- Registered check plug-in names: `bluenet_ema`.

### Validation

- Package-specific tests: `tests/test_bachmann_ema_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
