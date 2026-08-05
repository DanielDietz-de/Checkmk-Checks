# ERA MSS Target Processor Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0p15-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p15-blue)
<!-- compatibility-badges:end -->

SNMP monitoring for the ERA MSS (Multi-Sensor Surveillance) target processor system from [era.aero](https://www.era.aero/). One check plugin per subsystem produces services for the receiver, transmitter, target processor virtual server, remoter, BVIM, MUSR and NTP status, mapping the vendor status values (`OKA`, `WAR`, `n/a`) to Checkmk OK / WARN / UNKNOWN.

## How it works

All sections are detected via the ERA private enterprise prefix:

```text
sysObjectID startswith .1.3.6.1.4.1.11588.1.5.111   (bvim base)
sysObjectID contains   .1.3.6.1.4.1.311.1.1.3.1.2   (Windows host running the TP)
```

OID base is `.1.3.6.1.4.1.11588.1.5` (ERA MIB). Each subsystem walks its own sub-tree; the shared helper [`utils.py`](src/era_mss/agent_based/utils.py) normalises status values and emits `Result` objects, flagging only the fields that are actually considered "monitored" (the per-field `mon` flag in each parser). Fields like raw CPU / memory / drive usage numbers are reported as info only.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/era_mss/agent_based/utils.py` | Shared detect, discovery and check helpers; status map `OKA/WAR/n/a -> OK/WARN/UNKNOWN`. |
| `src/era_mss/agent_based/bvim.py` | `ERA BVIM` single service (power / DIN status on tp1 and tp2). |
| `src/era_mss/agent_based/vserver.py` | `ERA vServer <idx>` per target processor virtual server (sw, processes, time sync, CPU, memory, drives, LANs). |
| `src/era_mss/agent_based/rx.py` | `ERA <site>` receivers (status, power, FO A/B, mode counters). |
| `src/era_mss/agent_based/tx.py` | `ERA <item>` transmitters. |
| `src/era_mss/agent_based/rmtr.py` | `ERA <item>` remoters. |
| `src/era_mss/agent_based/musr.py` | `ERA MUSR` single service. |
| `src/era_mss/agent_based/ntp.py` | `ERA NTP` single service. |

## Installation

1. Install the MKP on the Checkmk site.
2. Add the ERA MSS device as an SNMP host. Ensure the community / v3 credentials allow reading `.1.3.6.1.4.1.11588.1.5`.
3. Run service discovery.

## Services

- `ERA BVIM`
- `ERA vServer <index>`
- `ERA <site>` — one per RX receiver, TX transmitter and RMTR remoter
- `ERA MUSR`
- `ERA NTP`

## Known limitations

- The `info` file declares destination paths under `era_surveillance_systems/...` while the source on disk lives under `era_mss/...`. The MKP will be packed from whatever the `info` file lists, so double-check the destination namespace before shipping.
- Packaged version is a dev build (`1.0.0-dev3`).

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `era_mss` version `1.0.1`; minimum Checkmk version `2.4.0p15`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `era_mss/src/info`; it declares 24 packaged files.
- Repository MKP artifacts present: `era_mss-1.0.0-dev1.mkp`, `era_mss-1.0.0-dev2.mkp`, `era_mss-1.0.0-dev3.mkp`, `era_mss-1.0.0-dev4.mkp`, `era_mss-1.0.0.mkp`, `era_mss-1.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/era_mss/agent_based/bvim.py`, `src/era_mss/agent_based/main.py`, `src/era_mss/agent_based/musr.py`, `src/era_mss/agent_based/ntp.py`, `src/era_mss/agent_based/outchann.py`, `src/era_mss/agent_based/rmtr.py`, `src/era_mss/agent_based/rx.py`, `src/era_mss/agent_based/switch.py` and 3 more.
- **Rulesets:** `src/era_mss/rulesets/era_outchann.py`, `src/era_mss/rulesets/era_rx.py`, `src/era_mss/rulesets/era_vserver.py`.
- **Check manuals:** `src/era_mss/checkman/era_bvim`, `src/era_mss/checkman/era_main`, `src/era_mss/checkman/era_musr`, `src/era_mss/checkman/era_ntp`, `src/era_mss/checkman/era_outchann`, `src/era_mss/checkman/era_rmtr`, `src/era_mss/checkman/era_rx`, `src/era_mss/checkman/era_switch` and 2 more.
- Registered check plug-in names: `era_bvim`, `era_main`, `era_musr`, `era_ntp`, `era_outchann`, `era_rmtr`, `era_rx`, `era_switch`, `era_tx`, `era_vserver`.

### Validation

- Package-specific tests: `tests/test_era_mss_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
