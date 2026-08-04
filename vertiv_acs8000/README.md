# Vertiv Avocent ACS 8000 console server

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p4-blue)
<!-- compatibility-badges:end -->

SNMP checks for Vertiv Avocent ACS 8000 Series console servers:
- Device info (model, firmware, serial)
- Power supply status
- Active sessions count
- CPU temperature
- Per serial port: connection state and RX/TX rate

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `vertiv_acs8000` version `1.0.0`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `vertiv_acs8000/src/info`; it declares 14 packaged files.
- Repository MKP artifacts present: `vertiv_acs8000-1.0.0.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/vertiv_acs8000/agent_based/cpu_temperature.py`, `src/vertiv_acs8000/agent_based/info.py`, `src/vertiv_acs8000/agent_based/psu.py`, `src/vertiv_acs8000/agent_based/serial_port.py`, `src/vertiv_acs8000/agent_based/sessions.py`.
- **Rulesets:** `src/vertiv_acs8000/rulesets/cpu_temperature.py`, `src/vertiv_acs8000/rulesets/psu.py`, `src/vertiv_acs8000/rulesets/serial_port.py`, `src/vertiv_acs8000/rulesets/sessions.py`.
- **Check manuals:** `src/vertiv_acs8000/checkman/vertiv_acs8000_cpu_temperature`, `src/vertiv_acs8000/checkman/vertiv_acs8000_info`, `src/vertiv_acs8000/checkman/vertiv_acs8000_psu`, `src/vertiv_acs8000/checkman/vertiv_acs8000_serial_port`, `src/vertiv_acs8000/checkman/vertiv_acs8000_sessions`.
- Registered check plug-in names: `vertiv_acs8000_cpu_temperature`, `vertiv_acs8000_info`, `vertiv_acs8000_psu`, `vertiv_acs8000_serial_port`, `vertiv_acs8000_sessions`.

### Validation

- Package-specific tests: `tests/test_vertiv_acs8000_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
