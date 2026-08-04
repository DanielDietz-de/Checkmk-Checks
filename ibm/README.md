# IBM Tape Library

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p5-blue)
<!-- compatibility-badges:end -->

SNMP monitoring for IBM TS4300 tape libraries. A single `Library Info` service per host reports the library model, serial number, firmware version, and description.

## How it works

The section is fetched via SNMP from `.1.3.6.1.4.1.14851.3.1.3`:

- `.1.0` — model (e.g. `3573-TL`)
- `.2.0` — serial number
- `.3.0` — vendor (used for detection)
- `.4.0` — firmware version
- `.5.0` — description

Detection matches when `.1.3.6.1.4.1.14851.3.1.3.3.0` matches `IBM`. The check always reports OK with a summary line containing all four fields.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/cmk_addons_plugins/ibm/agent_based/ts4300.py` | SNMP section parser and check plugin. |

## Installation

1. Install the MKP on the Checkmk site.
2. Configure SNMP access to the tape library.
3. Run service discovery — a single `Library Info` service is created.

## Services & metrics

- **Service:** `Library Info`
- **Summary:** `Model: <m>, Serial: <s>, Version: <v>, Description: <d>`
- **State:** always OK (informational).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `ibm` version `2.0.3`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `ibm/src/info`; it declares 1 packaged files.
- Repository MKP artifacts present: `ibm-2.0.0.mkp`, `ibm-2.0.1.mkp`, `ibm-2.0.2.mkp`, `ibm-2.0.3.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/ibm/agent_based/ts4300.py`.
- Registered check plug-in names: `ibm_ts4300`.

### Validation

- Package-specific tests: `tests/test_ibm_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
