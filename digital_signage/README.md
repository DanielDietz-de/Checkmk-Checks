# Digital Signage Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p8-blue)
<!-- compatibility-badges:end -->

Monitors GPU engine load on Windows hosts used as digital signage players (shop displays, airport screens, etc.). A PowerShell agent plugin samples the `GPUPerformanceCounters` WMI class and reports utilisation of the 3D, Copy, VideoProcessing and VideoDecode engines as a single Checkmk service.

## How it works

The Windows agent plugin `digital_signage.ps1` queries `Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine`, aggregates utilisation per engine name suffix (`_3D`, `_Copy`, `_VideoProcessing`, `_VideoDecode`) and emits one line per counter:

```text
<<<digital_signage:sep(124)>>>
GPU_Load 3D|12
GPU_Load Copy|0
GPU_Load VideoProcessing|34
GPU_Load VideoDecode|7
```

The check plugin `digital_signage` parses the section into a dict, then per counter name runs `check_levels` with the matching WATO upper level and emits a metric named after the counter (lowercase, spaces replaced with `_`). The discovered service is `Digital Signage`.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/digital_signage.ps1` | Windows PowerShell agent plugin (GPU counters via WMI). |
| `src/digital_signage/agent_based/digital_signage.py` | Section parser and check plugin. |
| `src/digital_signage/agent_based/bakery.py` | Bakery hook for plugin deployment. |
| `src/digital_signage/rulesets/bakery.py` | Bakery rule (sync / cached / off). |
| `src/digital_signage/rulesets/rulesets.py` | Check parameter rule (upper levels per GPU engine). |
| `src/digital_signage/graphing/metrics.py` | Metric definitions. |

## Installation

1. Install the MKP on the Checkmk site.
2. Enable the Bakery rule *Digital Signage Monitoring (Windows)* for the signage hosts and bake the agent, or copy `src/agents/plugins/digital_signage.ps1` to the Windows agent's plugins directory manually.
3. Run service discovery. A single `Digital Signage` service is created.

## Configuration

Rule: **Setup -> Agents -> Agent rules -> digital_sinage: Digital Signage Monitoring (Windows)**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `deployment` | CascadingSingleChoice | `sync`, `cached` (with interval), or `do_not_deploy`. |

Rule: **Parameters for discovered services -> Applications -> Digital Signage**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `GPU_Load_3D` | SimpleLevels (upper) | WARN/CRIT on the 3D engine utilisation. |
| `GPU_Load_Copy` | SimpleLevels (upper) | WARN/CRIT on the Copy engine utilisation. |
| `GPU_Load_VideoProcessing` | SimpleLevels (upper) | WARN/CRIT on the VideoProcessing engine utilisation. |
| `GPU_Load_VideoDecode` | SimpleLevels (upper) | WARN/CRIT on the VideoDecode engine utilisation. |

Check default parameters ship with fixed upper levels of `(90, 95)` for every engine.

## Services & metrics

- **Service:** `Digital Signage` — one per host.
- **Metrics:** `gpu_load_3d`, `gpu_load_copy`, `gpu_load_videoprocessing`, `gpu_load_videodecode`.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `digital_signage` version `1.2.2`; minimum Checkmk version `2.3.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `digital_signage/src/info`; it declares 6 packaged files.
- Repository MKP artifacts present: `digital_signage-1.0.0.mkp`, `digital_signage-1.1.0.mkp`, `digital_signage-1.1.1.mkp`, `digital_signage-1.2.0.mkp`, `digital_signage-1.2.1.mkp`, `digital_signage-1.2.2.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/digital_signage/agent_based/bakery.py`, `src/digital_signage/agent_based/digital_signage.py`.
- **Rulesets:** `src/digital_signage/rulesets/bakery.py`, `src/digital_signage/rulesets/rulesets.py`.
- **Graphing:** `src/digital_signage/graphing/metrics.py`.
- **Other packaged source:** `src/agents/plugins/digital_signage.ps1`.
- Registered check plug-in names: `digital_signage`.

### Validation

- Package-specific tests: `tests/test_digital_signage_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- No direct remote-network client was detected in the current source.

### Troubleshooting

- Emitted Checkmk sections detected in source: `digital_signage`.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
