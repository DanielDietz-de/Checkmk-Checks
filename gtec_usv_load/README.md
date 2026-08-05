# Gtec USV Load

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

SNMP monitoring for the three-phase output load of gtec uninterruptible power supplies. One service per phase reports the load in percent with configurable WARN/CRIT upper levels.

## How it works

The section is fetched via SNMP from enterprise subtree `.1.3.6.1.4.1.935` and reads the three output load percentage OIDs from `.1.3.6.1.4.1.935.1.1.1.8.3`:

- `.5` — `upsThreePhaseOutputLoadPercentageR` (phase 1)
- `.6` — `upsThreePhaseOutputLoadPercentageS` (phase 2)
- `.7` — `upsThreePhaseOutputLoadPercentageT` (phase 3)

Detection triggers on hosts whose sysObjectID starts with `.1.3.6.1.4.1.935`. Raw values are divided by 10 (SNMP returns tenths of a percent) and evaluated against `levels` via `check_levels`. A service `OUT Load <phase>` is created per phase.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agent_based/gtec_usv_load.py` | SNMP section parser and check plugin. |

## Installation

1. Install the MKP on the Checkmk site.
2. Configure SNMP access to the UPS. No further discovery rule is required.
3. Run service discovery — three `OUT Load phase N` services will appear.

## Configuration

The plugin binds to the existing `ups_out_load` check ruleset.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `levels` | `(warn, crit)` in percent | Upper levels on phase output load. Default `(85, 90)`. |

## Services & metrics

- **Service:** `OUT Load phase 1`, `OUT Load phase 2`, `OUT Load phase 3`
- **Metric:** `out_load` (percent)

## Known limitations

- Uses the legacy pre-2.3 `register.snmp_section` / `register.check_plugin` API via `agent_based_api.v1`. Still loads on 2.3/2.4 as long as the legacy API is available.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `gtec_usv_load` version `1.1.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `gtec_usv_load/src/info`; it declares 2 packaged files.
- Repository MKP artifacts present: `gtec_usv_load-1.0.0.mkp`, `gtec_usv_load-1.0.1.mkp`, `gtec_usv_load-1.1.0.mkp`, `gtec_usv_load-1.1.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/gtec_usv_load/agent_based/gtec_usv_load.py`.
- **Check manuals:** `src/gtec_usv_load/checkman/gtec_usv_load`.
- Registered check plug-in names: `gtec_usv_load`.

### Validation

- Package-specific tests: `tests/test_gtec_usv_load_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
